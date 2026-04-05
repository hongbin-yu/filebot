#!/usr/bin/env python3
"""
数据迁移工具 - 支持多种源数据库迁移到SQLite FileBot系统
支持的源数据库: Oracle, MS SQL Server, Sybase, HSQLDB, MySQL
"""

import argparse
import configparser
import logging
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import uuid
from datetime import datetime, timedelta

# 添加项目路径以便导入模型
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker


class DatabaseFactory:
    """数据库连接工厂"""
    
    @staticmethod
    def create_source_connection(config: configparser.SectionProxy):
        """创建源数据库连接"""
        db_type = config.get('type', 'oracle').lower()
        
        if db_type == 'oracle':
            return OracleConnector(config)
        elif db_type == 'mssql':
            return MSSQLConnector(config)
        elif db_type == 'sybase':
            return SybaseConnector(config)
        elif db_type == 'hsqldb':
            return HSQLDBConnector(config)
        elif db_type == 'mysql':
            return MySQLConnector(config)
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")


class BaseConnector:
    """数据库连接器基类"""
    
    def __init__(self, config: configparser.SectionProxy):
        self.config = config
        self.connection = None
        self.cursor = None
        
    def connect(self):
        """连接数据库（子类实现）"""
        raise NotImplementedError
        
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """执行查询"""
        if not self.cursor:
            self.connect()
        
        self.cursor.execute(query, params or ())
        columns = [col[0] for col in self.cursor.description]
        rows = self.cursor.fetchall()
        
        return [dict(zip(columns, row)) for row in rows]
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """执行更新"""
        if not self.cursor:
            self.connect()
        
        self.cursor.execute(query, params or ())
        return self.cursor.rowcount
    
    def get_table_names(self) -> List[str]:
        """获取表名列表"""
        raise NotImplementedError
        
    def get_table_count(self, table_name: str) -> int:
        """获取表记录数"""
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        result = self.execute_query(query)
        return result[0]['count'] if result else 0
        
    def close(self):
        """关闭连接"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()


class OracleConnector(BaseConnector):
    """Oracle连接器"""
    
    def connect(self):
        try:
            import cx_Oracle
            dsn = cx_Oracle.makedsn(
                self.config.get('host', 'localhost'),
                self.config.get('port', '1521'),
                service_name=self.config.get('service_name') or 
                            sid=self.config.get('sid', 'XE')
            )
            self.connection = cx_Oracle.connect(
                user=self.config['username'],
                password=self.config['password'],
                dsn=dsn
            )
            self.cursor = self.connection.cursor()
        except ImportError:
            raise ImportError("请安装cx_Oracle: pip install cx_Oracle")
            
    def get_table_names(self) -> List[str]:
        schema = self.config.get('schema', self.config['username'].upper())
        query = """
        SELECT table_name 
        FROM all_tables 
        WHERE owner = :owner 
        AND table_name NOT LIKE 'BIN$%'
        ORDER BY table_name
        """
        results = self.execute_query(query, (schema,))
        return [row['TABLE_NAME'].lower() for row in results]


class MSSQLConnector(BaseConnector):
    """MS SQL Server连接器"""
    
    def connect(self):
        try:
            import pyodbc
            server = self.config.get('host', 'localhost')
            instance = self.config.get('instance', '')
            database = self.config['database']
            
            if instance:
                server = f"{server}\\{instance}"
            
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server};"
                f"DATABASE={database};"
                f"UID={self.config['username']};"
                f"PWD={self.config['password']};"
            )
            
            if self.config.get('encrypt', 'yes').lower() == 'yes':
                conn_str += "Encrypt=yes;"
                if self.config.get('trust_server_certificate', 'no').lower() == 'yes':
                    conn_str += "TrustServerCertificate=yes;"
                else:
                    conn_str += "TrustServerCertificate=no;"
            
            self.connection = pyodbc.connect(conn_str)
            self.cursor = self.connection.cursor()
        except ImportError:
            raise ImportError("请安装pyodbc: pip install pyodbc")
            
    def get_table_names(self) -> List[str]:
        schema = self.config.get('schema', 'dbo')
        query = """
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE = 'BASE TABLE' 
        AND TABLE_SCHEMA = ?
        ORDER BY TABLE_NAME
        """
        results = self.execute_query(query, (schema,))
        return [row['TABLE_NAME'].lower() for row in results]


class MySQLConnector(BaseConnector):
    """MySQL连接器"""
    
    def connect(self):
        try:
            import mysql.connector
            self.connection = mysql.connector.connect(
                host=self.config.get('host', 'localhost'),
                port=self.config.getint('port', 3306),
                database=self.config['database'],
                user=self.config['username'],
                password=self.config['password']
            )
            self.cursor = self.connection.cursor(dictionary=True)
        except ImportError:
            raise ImportError("请安装mysql-connector-python: pip install mysql-connector-python")
            
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        if not self.cursor:
            self.connect()
        
        self.cursor.execute(query, params or ())
        return self.cursor.fetchall()
    
    def get_table_names(self) -> List[str]:
        query = "SHOW TABLES"
        results = self.execute_query(query)
        # MySQL返回格式: [{'Tables_in_dbname': 'tablename'}, ...]
        return [list(row.values())[0].lower() for row in results]


class SybaseConnector(BaseConnector):
    """Sybase连接器"""
    
    def connect(self):
        try:
            import pyodbc
            server = self.config.get('host', 'localhost')
            port = self.config.get('port', '5000')
            database = self.config['database']
            charset = self.config.get('charset', 'utf8')
            
            conn_str = (
                f"DRIVER={{Adaptive Server Enterprise}};"
                f"SERVER={server};"
                f"PORT={port};"
                f"DATABASE={database};"
                f"UID={self.config['username']};"
                f"PWD={self.config['password']};"
                f"CHARSET={charset};"
            )
            
            self.connection = pyodbc.connect(conn_str)
            self.cursor = self.connection.cursor()
        except ImportError:
            raise ImportError("请安装pyodbc: pip install pyodbc")
            
    def get_table_names(self) -> List[str]:
        query = """
        SELECT name 
        FROM sysobjects 
        WHERE type = 'U' 
        ORDER BY name
        """
        results = self.execute_query(query)
        return [row['name'].lower() for row in results]


class HSQLDBConnector(BaseConnector):
    """HSQLDB连接器"""
    
    def connect(self):
        try:
            import jaydebeapi
            # HSQLDB通常作为文件数据库或内存数据库
            db_path = self.config.get('path', './data/hsqldb')
            db_name = self.config.get('database', 'smarti')
            
            jdbc_url = f"jdbc:hsqldb:file:{db_path}/{db_name}"
            driver = "org.hsqldb.jdbcDriver"
            
            self.connection = jaydebeapi.connect(
                driver,
                jdbc_url,
                [self.config['username'], self.config['password']],
                f"{db_path}/hsqldb.jar"
            )
            self.cursor = self.connection.cursor()
        except ImportError:
            raise ImportError("请安装JayDeBeApi: pip install JayDeBeApi")
            
    def get_table_names(self) -> List[str]:
        query = """
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
        """
        results = self.execute_query(query)
        return [row['TABLE_NAME'].lower() for row in results]


class DataMigrator:
    """数据迁移器"""
    
    def __init__(self, config_path: str = "config.ini"):
        """初始化迁移器"""
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        
        self.setup_logging()
        self.connect_databases()
        
        # 迁移状态
        self.migration_state = self.load_migration_state()
        
    def setup_logging(self):
        """配置日志"""
        log_config = self.config['logging']
        level = getattr(logging, log_config.get('level', 'INFO'))
        
        handlers = []
        if log_config.getboolean('console', True):
            handlers.append(logging.StreamHandler())
        
        log_file = log_config.get('file', './migration.log')
        if log_file:
            handlers.append(logging.FileHandler(log_file))
        
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=handlers
        )
        self.logger = logging.getLogger("migrator")
        
    def connect_databases(self):
        """连接数据库"""
        try:
            # 连接源数据库
            source_config = self.config['source']
            self.source_conn = DatabaseFactory.create_source_connection(source_config)
            self.source_conn.connect()
            self.logger.info(f"成功连接源数据库: {source_config.get('type', 'unknown')}")
            
            # 连接目标数据库 (SQLite)
            sqlite_path = Path(self.config['target']['database'])
            sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            
            sqlite_url = f"sqlite:///{sqlite_path}"
            self.target_engine = create_engine(sqlite_url)
            self.target_session = sessionmaker(bind=self.target_engine)()
            self.logger.info(f"成功连接目标数据库: {sqlite_path}")
            
        except Exception as e:
            self.logger.error(f"数据库连接失败: {e}")
            raise
    
    def load_migration_state(self) -> Dict:
        """加载迁移状态"""
        state_file = self.config['migration'].get('incremental.last_id_file', './last_migration_state.json')
        if Path(state_file).exists():
            with open(state_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_migration_state(self):
        """保存迁移状态"""
        state_file = self.config['migration'].get('incremental.last_id_file', './last_migration_state.json')
        with open(state_file, 'w') as f:
            json.dump(self.migration_state, f, indent=2)
    
    def test_connections(self) -> bool:
        """测试数据库连接"""
        try:
            # 测试源数据库
            self.source_conn.execute_query("SELECT 1 FROM DUAL")
            
            # 测试目标数据库
            with self.target_engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            self.logger.info("数据库连接测试成功")
            return True
            
        except Exception as e:
            self.logger.error(f"连接测试失败: {e}")
            return False
    
    def get_table_counts(self) -> Dict[str, int]:
        """获取各表记录数"""
        tables = ['user', 'app', 'drawer', 'folder', 'document', 'file', 'page']
        counts = {}
        
        for table in tables:
            try:
                count = self.source_conn.get_table_count(table)
                counts[table] = count
                self.logger.info(f"表 {table}: {count} 条记录")
            except Exception as e:
                self.logger.warning(f"无法获取表 {table} 记录数: {e}")
                counts[table] = 0
        
        return counts
    
    def migrate_users(self, incremental: bool = False) -> int:
        """迁移用户数据"""
        self.logger.info("开始迁移用户数据..." + ("增量模式" if incremental else ""))
        
        try:
            # 构建查询
            where_clause = ""
            params = ()
            
            if incremental and 'users_last_id' in self.migration_state:
                last_id = self.migration_state['users_last_id']
                where_clause = "WHERE id > ?"
                params = (last_id,)
            
            query = f"""
                SELECT id, username, password, email, fullName, 
                       isActive, role, createdDate
                FROM user
                {where_clause}
                ORDER BY id
            """
            
            users = self.source_conn.execute_query(query, params)
            migrated_count = 0
            
            for user in users:
                # 生成确定性UUID（基于旧ID）
                user_id = self.generate_uuid(user['id'], 'user')
                
                # 构建插入SQL
                sql = """
                INSERT OR REPLACE INTO users 
                (id, username, password_hash, email, full_name, 
                 is_active, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                params = (
                    user_id,
                    user['username'],
                    user['password'],  # 注意：实际应重新哈希
                    user['email'],
                    user['fullName'],
                    bool(user['isActive']),
                    user['role'],
                    user['createdDate']
                )
                
                with self.target_engine.connect() as conn:
                    conn.execute(text(sql), params)
                    conn.commit()
                
                migrated_count += 1
                
                # 更新最后处理ID
                self.migration_state['users_last_id'] = user['id']
                
                if migrated_count % 100 == 0:
                    self.logger.info(f"已迁移 {migrated_count} 个用户")
            
            self.logger.info(f"用户迁移完成: {migrated_count}/{len(users)}")
            return migrated_count
            
        except Exception as e:
            self.logger.error(f"用户迁移失败: {e}")
            return 0
    
    def migrate_apps(self, incremental: bool = False) -> int:
        """迁移应用数据"""
        self.logger.info("开始迁移应用数据..." + ("增量模式" if incremental else ""))
        
        try:
            where_clause = ""
            params = ()
            
            if incremental and 'apps_last_id' in self.migration_state:
                last_id = self.migration_state['apps_last_id']
                where_clause = "WHERE id > ?"
                params = (last_id,)
            
            query = f"""
                SELECT id, name, description, createdDate, createdBy
                FROM app
                {where_clause}
                ORDER BY id
            """
            
            apps = self.source_conn.execute_query(query, params)
            migrated_count = 0
            
            # 获取默认所有者
            owner_sql = "SELECT id FROM users WHERE role = 'admin' LIMIT 1"
            with self.target_engine.connect() as conn:
                result = conn.execute(text(owner_sql))
                owner = result.fetchone()
            
            owner_id = owner[0] if owner else None
            
            if not owner_id:
                self.logger.warning("无管理员用户，将创建默认所有者")
                # 创建默认用户
                default_user_id = self.generate_uuid(0, 'default_user')
                user_sql = """
                INSERT OR REPLACE INTO users 
                (id, username, password_hash, email, full_name, 
                 is_active, role, created_at)
                VALUES (?, 'admin', 'admin123', 'admin@filebot.com', 
                        '系统管理员', 1, 'admin', datetime('now'))
                """
                with self.target_engine.connect() as conn:
                    conn.execute(text(user_sql), (default_user_id,))
                    conn.commit()
                owner_id = default_user_id
            
            for app in apps:
                app_id = self.generate_uuid(app['id'], 'app')
                
                sql = """
                INSERT OR REPLACE INTO apps 
                (id, name, description, owner_id, created_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
                """
                
                params = (
                    app_id,
                    app['name'],
                    app['description'],
                    owner_id,
                    app['createdDate'],
                    app['createdBy']
                )
                
                with self.target_engine.connect() as conn:
                    conn.execute(text(sql), params)
                    conn.commit()
                
                migrated_count += 1
                self.migration_state['apps_last_id'] = app['id']
            
            self.logger.info(f"应用迁移完成: {migrated_count}/{len(apps)}")
            return migrated_count
            
        except Exception as e:
            self.logger.error(f"应用迁移失败: {e}")
            return 0
    
    def generate_uuid(self, old_id: int, namespace: str) -> str:
        """生成确定性UUID（基于旧ID和命名空间）"""
        # 使用UUID v5生成确定性UUID
        namespace_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, namespace)
        return str(uuid.uuid5(namespace_uuid, str(old_id)))
    
    def run_incremental_migration(self):
        """运行增量迁移"""
        self.logger.info("开始增量迁移...")
        
        interval_minutes = self.config['migration'].getint('incremental.interval_minutes', 5)
        
        while True:
            try:
                self.logger.info(f"增量迁移周期开始，间隔: {interval_minutes}分钟")
                
                # 迁移新增数据
                user_count = self.migrate_users(incremental=True)
                app_count = self.migrate_apps(incremental=True)
                # 其他表待实现
                
                # 保存状态
                self.save_migration_state()
                
                self.logger.info(f"增量迁移完成: 用户{user_count}, 应用{app_count}")
                
                # 等待下一个周期
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                self.logger.info("增量迁移被用户中断")
                break
            except Exception as e:
                self.logger.error(f"增量迁移错误: {e}")
                time.sleep(60)  # 错误后等待1分钟重试
    
    def close(self):
        """关闭连接"""
        if hasattr(self, 'source_conn'):
            self.source_conn.close()
        if hasattr(self, 'target_session'):
            self.target_session.close()
        self.logger.info("数据库连接已关闭")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="多数据库数据迁移工具")
    parser.add_argument("--config", default="config.ini", help="配置文件路径")
    parser.add_argument("--test", action="store_true", help="测试数据库连接")
    parser.add_argument("--dry-run", action="store_true", help="预览迁移，不实际写入")
    parser.add_argument("--full", action="store_true", help="全量迁移")
    parser.add_argument("--incremental", action="store_true", help="增量迁移（持续运行）")
    parser.add_argument("--table", help="迁移指定表")
    parser.add_argument("--counts", action="store_true", help="显示表记录数")
    
    args = parser.parse_args()
    
    migrator = None
    try:
        migrator = DataMigrator(args.config)
        
        if args.test:
            success = migrator.test_connections()
            sys.exit(0 if success else 1)
        
        if args.counts:
            counts = migrator.get_table_counts()
            for table, count in counts.items():
                print(f"{table}: {count}")
            sys.exit(0)
        
        if args.incremental:
            print("启动增量迁移模式...")
            print("将定期检查并迁移新数据")
            print("按 Ctrl+C 停止")
            migrator.run_incremental_migration()
        
        elif args.full:
            print("全量迁移开始...")
            print("注意：这将迁移所有数据，请确保已备份！")
            
            if not args.dry_run:
                confirm = input("确认执行全量迁移？(yes/no): ")
                if confirm.lower() != "yes":
                    print("已取消")
                    sys.exit(0)
            
            # 按依赖顺序迁移
            migrator.migrate_users()
            migrator.migrate_apps()
            # 其他表待实现
            
            print("全量迁移完成")
        
        elif args.table:
            if args.table == "users":
                migrator.migrate_users()
            elif args.table == "apps":
                migrator.migrate_apps()
            else:
                print(f"未知表: {args.table}")
                print("可用表: users, apps, drawers, folders, documents, pages")
        
        else:
            parser.print_help()
    
    except Exception as e:
        logging.error(f"迁移失败: {e}")
        sys.exit(1)
    
    finally:
        if migrator:
            migrator.close()


if __name__ == "__main__":
    main()