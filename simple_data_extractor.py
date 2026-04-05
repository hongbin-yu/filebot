#!/usr/bin/env python3
"""
简化数据提取器 - 专注于从PO.TXT提取业务数据
"""

import re
import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class PersonRecord:
    """人员记录"""
    line_number: int
    date: str           # 日期: MM/DD/YY
    status: str         # 状态代码: E, I等
    initials: str       # 缩写: BD, DL等
    first_name: str     # 名: BRIAN, DANNY等
    last_name: str      # 姓: DEARB, LEUNG等
    raw_line: str       # 原始行内容
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "line_number": self.line_number,
            "date": self.date,
            "status": self.status,
            "initials": self.initials,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": f"{self.first_name} {self.last_name}",
            "raw_line_preview": repr(self.raw_line[:80]) if self.raw_line else ""
        }
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"行{self.line_number}: {self.date} {self.status} {self.initials} {self.first_name} {self.last_name}"

@dataclass
class CompanyInfo:
    """公司信息"""
    line_number: int
    company_name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "line_number": self.line_number,
            "company_name": self.company_name,
            "address": self.address,
            "phone": self.phone,
            "fax": self.fax
        }

class SimpleDataExtractor:
    """简化数据提取器"""
    
    def __init__(self):
        self.person_records: List[PersonRecord] = []
        self.company_info: List[CompanyInfo] = []
        self.other_data: Dict[str, Any] = {}
        
    def extract_from_file(self, file_path: str) -> Dict[str, Any]:
        """从文件提取数据"""
        print(f"从文件提取数据: {file_path}")
        
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        
        content = raw_data.decode('latin-1')
        lines = content.splitlines()
        
        print(f"总行数: {len(lines)}")
        
        # 提取数据
        self._extract_person_records(lines)
        self._extract_company_info(lines)
        self._extract_other_data(lines)
        
        # 生成汇总报告
        summary = self._generate_summary()
        
        return summary
    
    def _extract_person_records(self, lines: List[str]):
        """提取人员记录"""
        print("\n提取人员记录...")
        
        for i, line in enumerate(lines):
            if not line.strip():
                continue
                
            # 检查是否是以"-"开头的数据行
            if line[0] == '-' and len(line.strip()) > 1:
                # 清理空字符并按空格分割
                clean_line = line.replace('\x00', ' ').strip()
                parts = clean_line.split()
                
                # 检查是否包含足够的数据部分
                if len(parts) >= 6:
                    # 验证第一个部分是"-"
                    if parts[0] != '-':
                        continue
                    
                    # 验证日期格式
                    date_part = parts[1]
                    if not re.match(r'\d{2}/\d{2}/\d{2}', date_part):
                        continue
                    
                    # 创建记录
                    record = PersonRecord(
                        line_number=i + 1,
                        date=date_part,
                        status=parts[2] if len(parts) > 2 else "",
                        initials=parts[3] if len(parts) > 3 else "",
                        first_name=parts[4] if len(parts) > 4 else "",
                        last_name=parts[5] if len(parts) > 5 else "",
                        raw_line=line
                    )
                    
                    self.person_records.append(record)
        
        print(f"  找到 {len(self.person_records)} 条人员记录")
        
        # 打印示例
        if self.person_records:
            print("  前5条记录:")
            for j in range(min(5, len(self.person_records))):
                print(f"    {self.person_records[j]}")
    
    def _extract_company_info(self, lines: List[str]):
        """提取公司信息"""
        print("\n提取公司信息...")
        
        current_company = None
        
        for i, line in enumerate(lines):
            if not line.strip():
                continue
                
            # 查找公司名称（包含"PARKER HANNIFIN"的行）
            if "PARKER HANNIFIN" in line:
                # 提取公司名称
                clean_line = line.replace('\x00', ' ').strip()
                company_name_match = re.search(r'PARKER HANNIFIN[\w\s]*', clean_line)
                if company_name_match:
                    company_name = company_name_match.group(0).strip()
                    
                    current_company = CompanyInfo(
                        line_number=i + 1,
                        company_name=company_name
                    )
                    self.company_info.append(current_company)
            
            # 查找电话号码
            if current_company and not current_company.phone:
                phone_match = re.search(r'\(\d{3}\) \d{3}-\d{4}', line)
                if phone_match and "PH#" in line:
                    current_company.phone = phone_match.group(0)
            
            # 查找传真号码
            if current_company and not current_company.fax:
                fax_match = re.search(r'\(\d{3}\) \d{3}-\d{4}', line)
                if fax_match and "FAX" in line:
                    current_company.fax = fax_match.group(0)
            
            # 查找地址
            if current_company and not current_company.address:
                # 查找包含"WAY"或"CA"的行作为地址
                if "WAY" in line or "CA" in line:
                    clean_line = line.replace('\x00', ' ').strip()
                    # 提取地址部分（跳过前面的空格）
                    address_part = clean_line.lstrip()
                    if address_part and not address_part.startswith('PH#') and not address_part.startswith('FAX'):
                        current_company.address = address_part
        
        print(f"  找到 {len(self.company_info)} 条公司信息")
        if self.company_info:
            for company in self.company_info:
                print(f"    行{company.line_number}: {company.company_name}")
                if company.phone:
                    print(f"      电话: {company.phone}")
                if company.fax:
                    print(f"      传真: {company.fax}")
                if company.address:
                    print(f"      地址: {company.address}")
    
    def _extract_other_data(self, lines: List[str]):
        """提取其他数据"""
        print("\n提取其他数据...")
        
        # 查找所有日期
        all_dates = []
        for i, line in enumerate(lines):
            dates = re.findall(r'\d{2}/\d{2}/\d{2}', line)
            for date in dates:
                all_dates.append((i+1, date))
        
        # 查找所有零件号（格式: XXX-XXXXX）
        part_numbers = []
        for i, line in enumerate(lines):
            parts = re.findall(r'\d+-\d+', line)
            for part in parts:
                part_numbers.append((i+1, part))
        
        # 查找所有可能的产品描述
        product_descriptions = []
        for i, line in enumerate(lines):
            # 查找类似"3 PLATE MOLD"的描述
            if "PLATE" in line or "MOLD" in line:
                clean_line = line.replace('\x00', ' ').strip()
                # 提取描述部分（跳过行号等）
                if len(clean_line) > 10 and not clean_line.startswith(('0', '1', '-', ' ')):
                    product_descriptions.append((i+1, clean_line[:50]))
        
        self.other_data = {
            "dates": {
                "count": len(all_dates),
                "unique": len(set(d[1] for d in all_dates)),
                "samples": all_dates[:10]
            },
            "part_numbers": {
                "count": len(part_numbers),
                "unique": len(set(p[1] for p in part_numbers)),
                "samples": part_numbers[:10]
            },
            "product_descriptions": {
                "count": len(product_descriptions),
                "samples": product_descriptions[:5]
            }
        }
        
        print(f"  日期: {len(all_dates)} 个 ({len(set(d[1] for d in all_dates))} 个唯一)")
        print(f"  零件号: {len(part_numbers)} 个 ({len(set(p[1] for p in part_numbers))} 个唯一)")
        print(f"  产品描述: {len(product_descriptions)} 个")
    
    def _generate_summary(self) -> Dict[str, Any]:
        """生成汇总报告"""
        summary = {
            "extraction_time": datetime.now().isoformat(),
            "person_records": {
                "count": len(self.person_records),
                "records": [record.to_dict() for record in self.person_records],
                "statistics": {
                    "unique_dates": len(set(r.date for r in self.person_records)),
                    "unique_statuses": len(set(r.status for r in self.person_records)),
                    "unique_initials": len(set(r.initials for r in self.person_records)),
                    "unique_names": len(set(f"{r.first_name} {r.last_name}" for r in self.person_records))
                }
            },
            "company_info": [company.to_dict() for company in self.company_info],
            "other_data": self.other_data,
            "summary_text": self._create_summary_text()
        }
        
        return summary
    
    def _create_summary_text(self) -> str:
        """创建文本摘要"""
        lines = []
        lines.append(f"数据提取完成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"人员记录: {len(self.person_records)} 条")
        lines.append(f"公司信息: {len(self.company_info)} 条")
        
        if self.person_records:
            lines.append("\n人员记录统计:")
            # 按日期分组
            date_groups = {}
            for record in self.person_records:
                if record.date not in date_groups:
                    date_groups[record.date] = []
                date_groups[record.date].append(record)
            
            for date, records in sorted(date_groups.items()):
                lines.append(f"  {date}: {len(records)} 条记录")
            
            # 按状态分组
            status_groups = {}
            for record in self.person_records:
                if record.status not in status_groups:
                    status_groups[record.status] = []
                status_groups[record.status].append(record)
            
            lines.append("\n状态统计:")
            for status, records in sorted(status_groups.items()):
                lines.append(f"  {status}: {len(records)} 条记录")
        
        if self.company_info:
            lines.append("\n公司信息:")
            for company in self.company_info:
                lines.append(f"  {company.company_name}")
                if company.phone:
                    lines.append(f"    电话: {company.phone}")
                if company.address:
                    lines.append(f"    地址: {company.address}")
        
        return "\n".join(lines)
    
    def export_json(self, file_path: str):
        """导出为JSON文件"""
        summary = self._generate_summary()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"已导出到: {file_path}")
    
    def print_detailed_report(self):
        """打印详细报告"""
        print("\n" + "="*60)
        print("数据提取详细报告")
        print("="*60)
        
        print(self._create_summary_text())
        
        # 显示完整的人员记录
        if self.person_records:
            print(f"\n完整人员记录列表 ({len(self.person_records)} 条):")
            for i, record in enumerate(self.person_records):
                print(f"  {i+1:3}. 行{record.line_number:4}: {record.date} {record.status:2} {record.initials:3} {record.first_name:10} {record.last_name:10}")


def main():
    """主函数"""
    print("简化数据提取器 - PO.TXT业务数据提取")
    print("="*60)
    
    # 创建提取器
    extractor = SimpleDataExtractor()
    
    # 提取数据
    summary = extractor.extract_from_file("PO.TXT")
    
    # 打印详细报告
    extractor.print_detailed_report()
    
    # 导出结果
    extractor.export_json("po_business_data.json")
    
    # 生成提取摘要文件
    with open("po_extraction_summary.txt", "w", encoding="utf-8") as f:
        f.write(extractor._create_summary_text())
    print(f"\n提取摘要已保存到: po_extraction_summary.txt")
    
    print("\n" + "="*60)
    print("提取完成!")
    print("="*60)


if __name__ == "__main__":
    main()