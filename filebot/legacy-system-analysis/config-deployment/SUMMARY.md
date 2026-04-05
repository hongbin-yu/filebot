# 旧系统 (smarti) 配置与部署分析

## 概述
旧系统采用传统的Java EE技术栈，基于Spring、Hibernate、Apache Tiles等框架构建。系统使用Ant作为构建工具，部署在Tomcat应用服务器上。

## 技术栈配置

### 1. Web应用配置 (web.xml)

#### 1.1 主要组件
- **Servlet规范**：2.3 (Java EE 1.3)
- **安全框架**：Acegi Security (Spring Security前身)
- **MVC框架**：WebWork (Struts 2前身)
- **模板引擎**：Apache Tiles 2.0
- **AJAX框架**：DWR (Direct Web Remoting)

#### 1.2 过滤器配置
```xml
<!-- 安全过滤器 -->
<filter>
    <filter-name>acegi_filter_chain_proxy</filter-name>
    <filter-class>org.acegisecurity.util.FilterToBeanProxy</filter-class>
</filter>

<!-- WebWork过滤器 -->
<filter>
    <filter-name>webwork</filter-name>
    <filter-class>com.opensymphony.webwork.dispatcher.FilterDispatcher</filter-class>
</filter>

<!-- Tiles过滤器 -->
<filter>
    <filter-name>Tiles Filter</filter-name>
    <filter-class>org.apache.tiles.filter.TilesFilter</filter-class>
</filter>
```

#### 1.3 Servlet配置
```xml
<!-- Tiles Servlet -->
<servlet>
    <servlet-name>tiles</servlet-name>
    <servlet-class>org.apache.tiles.servlets.TilesServlet</servlet-class>
</servlet>

<!-- DWR Servlet (AJAX) -->
<servlet>
    <servlet-name>dwr</servlet-name>
    <servlet-class>org.directwebremoting.servlet.DwrServlet</servlet-class>
</servlet>
```

#### 1.4 会话配置
```xml
<session-config>
    <session-timeout>60</session-timeout> <!-- 60分钟 -->
</session-config>
```

### 2. Spring框架配置

#### 2.1 配置文件结构
```
/WEB-INF/
├── spring-applicationContext.xml          # 主应用上下文
├── spring-applicationContextMaster.xml    # 主数据库配置
├── spring-applicationContextSlaver.xml    # 从数据库配置
├── spring-acegi.xml                      # 安全配置
├── spring-applicationContext-email.xml    # 邮件配置
├── spring-applicationContext-import.xml   # 导入配置
└── spring-applicationContext-ldap.xml     # LDAP配置
```

#### 2.2 主要Bean配置
- **数据源**：配置多个数据库连接（HSQLDB、Oracle、SQL Server、Sybase）
- **事务管理**：声明式事务管理（Spring Transaction）
- **Hibernate集成**：SessionFactory配置
- **服务层Bean**：业务服务组件
- **DAO层Bean**：数据访问对象

#### 2.3 安全配置 (Acegi Security)
- **认证方式**：表单登录、记住我功能
- **授权规则**：URL级别的安全控制
- **密码加密**：MD5/SHA哈希
- **会话管理**：会话固定防护

### 3. 数据库配置

#### 3.1 Hibernate配置 (hibernate.cfg.xml)
```xml
<hibernate-configuration>
    <session-factory>
        <!-- 数据库方言 -->
        <property name="dialect">org.hibernate.dialect.HSQLDialect</property>
        
        <!-- 连接属性 -->
        <property name="connection.url">jdbc:hsqldb:file:${db.home}/smarti</property>
        <property name="connection.username">sa</property>
        <property name="connection.password"></property>
        
        <!-- 映射文件 -->
        <mapping resource="com/smarti/entity/App.hbm.xml"/>
        <mapping resource="com/smarti/entity/Document.hbm.xml"/>
        <!-- ... 其他实体映射 -->
    </session-factory>
</hibernate-configuration>
```

#### 3.2 多数据库支持
系统支持多种数据库，通过不同的配置文件切换：
- `hibernate-smarti.cfg.xml` - HSQLDB（开发环境）
- `hibernate-sybase.cfg.xml` - Sybase ASE
- 其他数据库：Oracle, MS SQL Server

#### 3.3 数据库初始化
- **初始化脚本**：`src/cfg/hsql/smartiinit.sql`
- **存储过程**：`src/cfg/hsql/smartiprocedures.sql`
- **视图定义**：`src/cfg/hsql/smartiviews.sql`

### 4. 构建系统 (Ant)

#### 4.1 构建配置文件 (build.xml)
```xml
<project name="smarti-admin" default="usage" basedir=".">
    <!-- 属性定义 -->
    <property name="dist.name" value="smarti" />
    <property name="tomcathome.dir" value="${tomcat.home}" />
    <property name="target.dir" value="${basedir}/target" />
    <property name="web.dir" value="${basedir}/web" />
    <!-- ... -->
</project>
```

#### 4.2 构建目标
- `compile` - 编译Java源代码
- `package` - 创建WAR/EAR文件
- `deploy` - 部署到Tomcat
- `clean` - 清理构建文件

#### 4.3 外部依赖
- **JAR文件位置**：`web/WEB-INF/lib/`（共100+个JAR）
- **主要依赖**：
  - Spring Framework 2.0.5
  - Hibernate 3.2.5
  - Apache Tiles 2.0
  - WebWork 2.2.7
  - Acegi Security 1.0.5
  - DWR 2.0.3

### 5. 文件存储配置

#### 5.1 文件路径配置
- **基础路径**：通过系统属性或配置文件设置
- **文件结构**：按应用/抽屉/文件夹层级组织
- **命名策略**：UUID文件名，避免冲突

#### 5.2 临时文件管理
- **上传临时目录**：Tomcat临时目录或指定路径
- **转换缓存**：转换后的PDF缓存文件
- **清理策略**：定期清理过期临时文件

### 6. 日志配置

#### 6.1 Log4j配置 (log4j.properties)
```properties
# 日志级别
log4j.rootLogger=INFO, stdout, file

# 控制台输出
log4j.appender.stdout=org.apache.log4j.ConsoleAppender
log4j.appender.stdout.layout=org.apache.log4j.PatternLayout
log4j.appender.stdout.layout.ConversionPattern=%d{yyyy-MM-dd HH:mm:ss} %-5p %c{1}:%L - %m%n

# 文件输出
log4j.appender.file=org.apache.log4j.RollingFileAppender
log4j.appender.file.File=${catalina.base}/logs/smarti.log
```

#### 6.2 审计日志
- **操作审计**：用户登录、文件操作等
- **安全审计**：权限检查、安全事件
- **系统审计**：系统启动、关闭、错误

### 7. 部署架构

#### 7.1 单机部署
```
Tomcat应用服务器
├── smarti.war (Web应用)
├── lib/ (共享库)
└── conf/ (服务器配置)
```

#### 7.2 集群部署（可选）
- **负载均衡**：前端负载均衡器
- **会话复制**：Tomcat集群会话复制
- **共享存储**：网络共享文件存储

#### 7.3 数据库部署
- **开发环境**：嵌入式HSQLDB
- **生产环境**：Oracle/MS SQL Server/Sybase集群

### 8. 配置管理策略

#### 8.1 环境特定配置
- **开发环境**：HSQLDB嵌入式数据库
- **测试环境**：独立数据库服务器
- **生产环境**：高可用数据库集群

#### 8.2 配置外部化
- **数据库连接**：JNDI数据源
- **文件路径**：系统属性或环境变量
- **邮件服务器**：配置文件外部化

#### 8.3 配置验证
- **启动验证**：应用启动时检查关键配置
- **运行监控**：运行时配置有效性检查
- **变更管理**：配置变更的审计和回滚

### 9. 性能调优配置

#### 9.1 连接池配置
- **最大连接数**：根据负载调整
- **超时设置**：连接获取和空闲超时
- **验证查询**：连接有效性验证

#### 9.2 缓存配置
- **Hibernate缓存**：二级缓存配置
- **查询缓存**：常用查询结果缓存
- **文件缓存**：转换结果缓存

#### 9.3 线程池配置
- **转换线程池**：并发转换任务控制
- **导入线程池**：批量导入任务控制
- **搜索线程池**：并发搜索请求控制

### 10. 新系统配置和部署建议

#### 10.1 配置现代化
| 旧系统配置 | 新系统建议 | 理由 |
|------------|------------|------|
| Ant构建 | Docker容器化 | 标准化部署，环境一致性 |
| Tomcat WAR部署 | 容器化微服务 | 灵活扩展，云原生支持 |
| 属性文件配置 | 环境变量 + 配置文件 | 12因素应用，安全合规 |
| Log4j日志 | 结构化日志 (JSON) | 便于集中日志分析 |

#### 10.2 部署简化
1. **统一数据库**：从多数据库支持简化为PostgreSQL/SQLite
2. **简化配置**：减少配置文件数量，使用分层配置
3. **容器化部署**：使用Docker和Docker Compose简化部署
4. **自动化CI/CD**：集成自动化测试和部署流水线

#### 10.3 配置迁移策略
1. **关键配置识别**：识别必须迁移的配置项
2. **格式转换**：从XML/属性文件转换为YAML/环境变量
3. **验证机制**：新配置系统的验证测试
4. **回滚预案**：配置迁移失败时的回滚方案

### 11. 安全配置注意事项

#### 11.1 认证和授权
- **迁移现有用户**：保持密码哈希兼容性或重置密码
- **权限映射**：将Acegi权限规则映射到新系统
- **会话管理**：保持类似的会话超时设置

#### 11.2 网络安全
- **输入验证**：保持或增强输入验证规则
- **文件上传安全**：类似的文件类型和大小限制
- **API安全**：添加API令牌认证

#### 11.3 审计合规
- **审计日志**：确保新系统提供同等或更好的审计能力
- **合规要求**：满足行业和法规合规要求
- **数据保护**：保持或增强数据保护措施

### 12. 监控和维护配置

#### 12.1 健康检查
- **应用健康**：添加/health端点
- **数据库健康**：数据库连接监控
- **文件系统健康**：存储空间和权限检查

#### 12.2 性能监控
- **响应时间**：API响应时间监控
- **资源使用**：CPU、内存、磁盘监控
- **业务指标**：上传数量、转换成功率等

#### 12.3 告警配置
- **错误率告警**：错误率超过阈值告警
- **资源告警**：磁盘空间、内存不足告警
- **业务告警**：关键业务流程失败告警

### 13. 结论

旧系统的配置和部署架构具有以下特点：
1. **传统但完整**：基于成熟的Java EE技术栈
2. **灵活配置**：支持多种数据库和环境
3. **企业级特性**：完整的安全、审计、监控配置
4. **部署复杂**：依赖多个外部组件和配置

**新系统设计原则**：
1. **简化配置**：减少配置文件数量，统一配置格式
2. **现代化部署**：采用容器化和云原生技术
3. **增强监控**：集成现代监控和告警系统
4. **保持兼容**：在安全、审计等关键领域保持兼容性

**迁移关键**：确保新系统在功能对等的基础上，提供更简单、更可靠、更易维护的配置和部署体验。