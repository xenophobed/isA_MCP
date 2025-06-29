#!/usr/bin/env python3
"""
Generate sample customs trade data for testing
生成海关贸易测试数据
"""

import random
import asyncio
import asyncpg
from datetime import datetime, timedelta
from decimal import Decimal
import json

# 数据生成配置
DATA_CONFIG = {
    'companies': 1000,      # 企业数量
    'declarations': 10000,  # 报关单数量
    'goods_details': 30000, # 商品明细数量 (平均每单3个商品)
    'containers': 8000,     # 集装箱数量
    'price_monitoring': 5000,  # 价格监控记录
    'risk_alerts': 500      # 风险预警记录
}

# 基础数据
COMPANY_TYPES = ['进口商', '出口商', '货代', '生产企业']
CREDIT_LEVELS = ['AA', 'A', 'B', 'C', 'D']
TRADE_TYPES = ['进口', '出口']
TRADE_MODES = ['0110', '0210', '0310', '1210', '9610']  # 贸易方式代码
TRANSPORT_MODES = ['2', '5', '1', '9']  # 运输方式：海运、航空、铁路、其他
CURRENCIES = ['USD', 'EUR', 'JPY', 'CNY']
STATUS_LIST = ['已申报', '已审核', '已放行', '查验中', '退单']
RISK_LEVELS = ['低风险', '中等风险', '高风险']

# 德国相关数据
GERMAN_COMPANIES = [
    'BMW AG', 'Mercedes-Benz Group AG', 'Volkswagen AG', 'Audi AG', 'Porsche AG',
    'Bosch GmbH', 'Continental AG', 'ZF Friedrichshafen AG', 'Mahle GmbH', 'Schaeffler AG'
]

GERMAN_BRANDS = [
    'BMW', 'Mercedes-Benz', 'Volkswagen', 'Audi', 'Porsche',
    'Bosch', 'Continental', 'ZF', 'Mahle', 'Schaeffler'
]

# 中国企业名称示例
CHINESE_COMPANIES = [
    '上海汽车进出口有限公司', '深圳市汽车零部件进口有限公司', '广州德国汽配贸易有限公司',
    '北京奔驰汽车配件有限公司', '天津大众汽车零件进口公司', '青岛宝马配件贸易有限公司',
    '宁波奥迪零配件进口有限公司', '苏州博世汽车配件有限公司', '杭州大陆汽车系统有限公司',
    '武汉采埃孚传动技术有限公司'
]

class CustomsDataGenerator:
    """海关数据生成器"""
    
    def __init__(self, db_config):
        self.db_config = db_config
        self.connection = None
        
    async def connect(self):
        """连接数据库"""
        self.connection = await asyncpg.connect(**self.db_config)
        print("Connected to database successfully")
    
    async def close(self):
        """关闭数据库连接"""
        if self.connection:
            await self.connection.close()
            print("Database connection closed")
    
    async def generate_all_data(self):
        """生成所有测试数据"""
        try:
            await self.connect()
            
            print("Starting data generation...")
            
            # 1. 生成企业数据
            print("Generating companies...")
            await self.generate_companies()
            
            # 2. 生成报关单数据
            print("Generating declarations...")
            await self.generate_declarations()
            
            # 3. 生成商品明细数据
            print("Generating goods details...")
            await self.generate_goods_details()
            
            # 4. 生成集装箱数据
            print("Generating containers...")
            await self.generate_containers()
            
            # 5. 生成价格监控数据
            print("Generating price monitoring data...")
            await self.generate_price_monitoring()
            
            # 6. 生成风险预警数据
            print("Generating risk alerts...")
            await self.generate_risk_alerts()
            
            # 7. 生成贸易关系数据
            print("Generating trade relationships...")
            await self.generate_trade_relationships()
            
            print("Data generation completed successfully!")
            
        except Exception as e:
            print(f"Error generating data: {e}")
            raise
        finally:
            await self.close()
    
    async def generate_companies(self):
        """生成企业数据"""
        companies_data = []
        
        for i in range(DATA_CONFIG['companies']):
            # 混合德国公司和中国公司
            if i < 100:  # 前100家使用真实德国公司名称
                company_name = f"{random.choice(GERMAN_COMPANIES)} {random.choice(['GmbH', 'AG', 'KG'])}"
                company_type = '出口商'
            elif i < 200:  # 接下来100家使用中国公司名称
                company_name = random.choice(CHINESE_COMPANIES)
                company_type = '进口商'
            else:  # 其余使用生成的名称
                if random.random() < 0.3:  # 30% 德国公司
                    company_name = f"德国{random.choice(['汽车', '机械', '化工', '电子'])}有限公司 第{i}分公司"
                    company_type = '出口商'
                else:  # 70% 中国公司
                    city = random.choice(['上海', '深圳', '广州', '北京', '天津', '青岛', '宁波', '苏州'])
                    industry = random.choice(['汽车', '机械', '电子', '化工', '纺织', '食品'])
                    company_name = f"{city}{industry}{'进出口' if random.random() < 0.5 else '贸易'}有限公司"
                    company_type = random.choice(COMPANY_TYPES)
            
            company_code = f"91{random.randint(100000000000000, 999999999999999)}"
            
            companies_data.append((
                company_code,
                company_name,
                company_type,
                random.choice(CREDIT_LEVELS),
                f"{random.choice(['上海市', '深圳市', '广州市', '北京市'])}某某区某某路{random.randint(1, 999)}号",
                f"从事{random.choice(['汽车零配件', '机械设备', '电子产品', '化工原料'])}的{'进口' if company_type == '进口商' else '出口'}业务",
                datetime.now().date() - timedelta(days=random.randint(365, 3650)),  # 1-10年前成立
                Decimal(str(random.uniform(1000000, 100000000))).quantize(Decimal('0.01'))  # 年贸易额
            ))
        
        # 批量插入
        await self.connection.executemany("""
            INSERT INTO companies (company_code, company_name, company_type, credit_level, 
                                 registration_address, business_scope, established_date, annual_trade_volume)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (company_code) DO NOTHING
        """, companies_data)
        
        print(f"Generated {len(companies_data)} companies")
    
    async def generate_declarations(self):
        """生成报关单数据"""
        # 获取企业代码
        companies = await self.connection.fetch("SELECT company_code, company_type FROM companies")
        
        # 获取港口代码
        ports = await self.connection.fetch("SELECT port_code FROM ports")
        port_codes = [port['port_code'] for port in ports]
        
        declarations_data = []
        start_date = datetime.now().date() - timedelta(days=365*2)  # 2年数据
        
        for i in range(DATA_CONFIG['declarations']):
            company = random.choice(companies)
            company_code = company['company_code']
            
            # 根据企业类型决定贸易类型
            if company['company_type'] == '进口商':
                trade_type = '进口'
                # 德国到中国
                departure_port = 'DEHAM'  # 汉堡港
                arrival_port = random.choice(['CNSHA', 'CNSZX', 'CNQIN', 'CNNGB'])
                origin_country = 'DEU'
                destination_country = 'CHN'
            else:
                trade_type = random.choice(['进口', '出口'])
                if trade_type == '进口':
                    departure_port = random.choice(['DEHAM', 'NLRTM', 'USNYC'])
                    arrival_port = random.choice(['CNSHA', 'CNSZX', 'CNQIN', 'CNNGB'])
                    origin_country = random.choice(['DEU', 'USA', 'JPN'])
                    destination_country = 'CHN'
                else:
                    departure_port = random.choice(['CNSHA', 'CNSZX', 'CNQIN', 'CNNGB'])
                    arrival_port = random.choice(['DEHAM', 'NLRTM', 'USNYC'])
                    origin_country = 'CHN'
                    destination_country = random.choice(['DEU', 'USA', 'JPN'])
            
            declare_date = start_date + timedelta(days=random.randint(0, 730))
            customs_date = declare_date + timedelta(days=random.randint(0, 3))
            release_date = customs_date + timedelta(days=random.randint(0, 7))
            
            # 生成金额 (德国汽车零配件通常价值较高)
            if origin_country == 'DEU' and trade_type == '进口':
                total_amount = Decimal(str(random.uniform(50000, 500000))).quantize(Decimal('0.01'))
            else:
                total_amount = Decimal(str(random.uniform(10000, 200000))).quantize(Decimal('0.01'))
            
            currency = random.choice(CURRENCIES)
            if currency == 'USD':
                exchange_rate = Decimal(str(random.uniform(6.8, 7.2))).quantize(Decimal('0.0001'))
            elif currency == 'EUR':
                exchange_rate = Decimal(str(random.uniform(7.5, 8.2))).quantize(Decimal('0.0001'))
            elif currency == 'JPY':
                exchange_rate = Decimal(str(random.uniform(0.045, 0.055))).quantize(Decimal('0.000001'))
            else:  # CNY
                exchange_rate = Decimal('1.0000')
            
            rmb_amount = total_amount * exchange_rate
            total_tax = rmb_amount * Decimal(str(random.uniform(0.05, 0.15)))  # 5-15% 税率
            
            prefix = "120" if trade_type == "进口" else "320"
            declaration_no = f"{prefix}{declare_date.strftime('%y%m%d')}{i:06d}"
            
            declarations_data.append((
                declaration_no,
                company_code,
                trade_type,
                random.choice(TRADE_MODES),
                random.choice(TRANSPORT_MODES),
                departure_port,
                arrival_port,
                destination_country,
                origin_country,
                declare_date,
                customs_date,
                release_date,
                total_amount,
                currency,
                exchange_rate,
                rmb_amount,
                total_tax,
                f"海关关员{random.randint(1001, 9999)}",
                random.choice(STATUS_LIST),
                random.choice(RISK_LEVELS)
            ))
        
        # 批量插入
        await self.connection.executemany("""
            INSERT INTO declarations (declaration_no, company_code, trade_type, trade_mode, transport_mode,
                                    departure_port, arrival_port, destination_country, origin_country,
                                    declare_date, customs_date, release_date, total_amount, currency_code,
                                    exchange_rate, rmb_amount, total_tax, customs_officer, status, risk_level)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)
            ON CONFLICT (declaration_no) DO NOTHING
        """, declarations_data)
        
        print(f"Generated {len(declarations_data)} declarations")
    
    async def generate_goods_details(self):
        """生成商品明细数据"""
        # 获取报关单
        declarations = await self.connection.fetch("SELECT declaration_no, trade_type, origin_country FROM declarations")
        
        # 获取HS编码
        hs_codes = await self.connection.fetch("SELECT hs_code, hs_description_cn FROM hs_codes")
        
        goods_data = []
        
        for declaration in declarations:
            declaration_no = declaration['declaration_no']
            trade_type = declaration['trade_type']
            origin_country = declaration['origin_country']
            
            # 每个报关单有1-5个商品
            goods_count = random.randint(1, 5)
            
            for seq in range(1, goods_count + 1):
                hs_code_data = random.choice(hs_codes)
                hs_code = hs_code_data['hs_code']
                goods_name = hs_code_data['hs_description_cn']
                
                # 德国汽车零配件的特殊处理
                if origin_country == 'DEU' and trade_type == '进口':
                    brand = random.choice(GERMAN_BRANDS)
                    model = f"{brand}-{random.choice(['A', 'B', 'C'])}{random.randint(100, 999)}"
                    manufacturer = f"{random.choice(GERMAN_COMPANIES)} Manufacturing"
                    unit_price = Decimal(str(random.uniform(500, 5000))).quantize(Decimal('0.01'))
                    quantity = Decimal(str(random.uniform(10, 500))).quantize(Decimal('0.001'))
                else:
                    brand = f"品牌{random.randint(1, 100)}"
                    model = f"型号{random.randint(1000, 9999)}"
                    manufacturer = f"制造商{random.randint(1, 100)}"
                    unit_price = Decimal(str(random.uniform(50, 1000))).quantize(Decimal('0.01'))
                    quantity = Decimal(str(random.uniform(50, 1000))).quantize(Decimal('0.001'))
                
                total_price = unit_price * quantity
                
                goods_data.append((
                    declaration_no,
                    seq,
                    hs_code,
                    goods_name,
                    f"规格：{random.choice(['标准型', '加强型', '豪华型'])}，{random.choice(['黑色', '银色', '白色'])}",
                    origin_country,
                    quantity,
                    random.choice(['千克', '个', '套', '台']),
                    quantity * Decimal(str(random.uniform(0.8, 1.2))),
                    random.choice(['件', '箱', '包']),
                    unit_price,
                    total_price,
                    random.choice(['USD', 'EUR', 'CNY']),
                    brand,
                    model,
                    manufacturer
                ))
        
        # 批量插入
        await self.connection.executemany("""
            INSERT INTO goods_details (declaration_no, seq_no, hs_code, goods_name, specifications,
                                     origin_country, quantity_1, unit_1, quantity_2, unit_2,
                                     unit_price, total_price, currency_code, brand, model, manufacturer)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
        """, goods_data)
        
        print(f"Generated {len(goods_data)} goods details")
    
    async def generate_containers(self):
        """生成集装箱数据"""
        # 获取报关单（只选择海运的）
        declarations = await self.connection.fetch("""
            SELECT declaration_no, departure_port, arrival_port 
            FROM declarations 
            WHERE transport_mode = '2'
            ORDER BY RANDOM()
            LIMIT $1
        """, DATA_CONFIG['containers'])
        
        container_data = []
        
        for i, declaration in enumerate(declarations):
            container_prefix = "TEMU" if random.random() < 0.5 else "MSCU"
            container_no = f"{container_prefix}{random.randint(1000000, 9999999)}"
            
            container_data.append((
                container_no,
                declaration['declaration_no'],
                random.choice(['GP', 'HQ', 'RF', 'OT']),  # 集装箱类型
                random.choice(['20', '40', '45']),  # 尺寸
                f"SEAL{random.randint(100000, 999999)}",  # 铅封号
                Decimal(str(random.uniform(15000, 30000))).quantize(Decimal('0.01')),  # 毛重
                declaration['departure_port'],
                declaration['arrival_port']
            ))
        
        # 批量插入
        await self.connection.executemany("""
            INSERT INTO containers (container_no, declaration_no, container_type, container_size,
                                  seal_no, gross_weight, loading_port, discharge_port)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (container_no) DO NOTHING
        """, container_data)
        
        print(f"Generated {len(container_data)} containers")
    
    async def generate_price_monitoring(self):
        """生成价格监控数据"""
        hs_codes = await self.connection.fetch("SELECT hs_code FROM hs_codes")
        
        price_data = []
        start_date = datetime.now().date() - timedelta(days=365)
        
        for _ in range(DATA_CONFIG['price_monitoring']):
            hs_code = random.choice(hs_codes)['hs_code']
            price_date = start_date + timedelta(days=random.randint(0, 365))
            
            # 德国汽车零配件价格通常较高
            base_price = random.uniform(100, 2000)
            reference_price = Decimal(str(base_price * random.uniform(0.9, 1.1))).quantize(Decimal('0.01'))
            
            price_data.append((
                hs_code,
                reference_price,
                price_date,
                random.choice(['海关估价', '市场价格', '同期价格', '国际市场价']),
                random.choice(['全球', '欧洲', '亚洲', '北美']),
                random.choice(['进口价', '出口价', '市场价'])
            ))
        
        await self.connection.executemany("""
            INSERT INTO price_monitoring (hs_code, reference_price, price_date, price_source, market_region, price_type)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, price_data)
        
        print(f"Generated {len(price_data)} price monitoring records")
    
    async def generate_risk_alerts(self):
        """生成风险预警数据"""
        declarations = await self.connection.fetch("SELECT declaration_no, company_code FROM declarations ORDER BY RANDOM() LIMIT $1", DATA_CONFIG['risk_alerts'])
        
        risk_types = [
            '价格异常', '重量异常', '数量异常', '品名不符', '归类错误',
            '单证不全', '许可证问题', '知识产权', '贸易管制', '反倾销'
        ]
        
        risk_data = []
        
        for declaration in declarations:
            risk_type = random.choice(risk_types)
            risk_level = random.choice(RISK_LEVELS)
            
            descriptions = {
                '价格异常': '申报价格明显低于同期同类商品价格',
                '重量异常': '申报重量与实际重量不符',
                '数量异常': '申报数量与实际数量存在差异',
                '品名不符': '申报品名与实际货物不符',
                '归类错误': 'HS编码归类可能错误'
            }
            
            risk_data.append((
                declaration['declaration_no'],
                declaration['company_code'],
                risk_type,
                risk_level,
                descriptions.get(risk_type, f'{risk_type}风险预警'),
                random.choice([True, False]),  # 是否已处理
                f"关员{random.randint(1001, 9999)}" if random.choice([True, False]) else None,
                datetime.now() - timedelta(days=random.randint(0, 30)) if random.choice([True, False]) else None
            ))
        
        await self.connection.executemany("""
            INSERT INTO risk_alerts (declaration_no, company_code, risk_type, risk_level, 
                                   risk_description, handled, handler, handle_time)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, risk_data)
        
        print(f"Generated {len(risk_data)} risk alerts")
    
    async def generate_trade_relationships(self):
        """生成贸易伙伴关系数据"""
        # 获取出口商和进口商
        exporters = await self.connection.fetch("SELECT company_code FROM companies WHERE company_type = '出口商'")
        importers = await self.connection.fetch("SELECT company_code FROM companies WHERE company_type = '进口商'")
        
        relationship_data = []
        
        # 生成100个贸易关系
        for _ in range(100):
            exporter = random.choice(exporters)['company_code']
            importer = random.choice(importers)['company_code']
            
            relationship_data.append((
                exporter,
                importer,
                random.randint(1, 50),  # 贸易频次
                Decimal(str(random.uniform(100000, 10000000))).quantize(Decimal('0.01')),  # 总贸易额
                [random.choice(['汽车零配件', '机械设备', '电子产品']) for _ in range(random.randint(1, 3))],  # 主要产品
                datetime.now().date() - timedelta(days=random.randint(365, 1095)),  # 关系开始时间
                Decimal(str(random.uniform(0.3, 1.0))).quantize(Decimal('0.01'))  # 关系强度
            ))
        
        await self.connection.executemany("""
            INSERT INTO trade_relationships (exporter_code, importer_code, trade_frequency, 
                                           total_trade_amount, main_products, relationship_start_date, relationship_strength)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, relationship_data)
        
        print(f"Generated {len(relationship_data)} trade relationships")

# 主函数
async def main():
    """主函数"""
    # 数据库配置
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'postgres',  # 先连接到默认数据库
        'user': 'xenodennis',    # 使用您的用户名
        'password': ''           # 如果有密码请填写
    }
    
    # 创建数据库和基础结构
    print("Setting up database...")
    conn = await asyncpg.connect(**db_config)
    
    # 创建测试数据库
    try:
        await conn.execute("CREATE DATABASE customs_trade_db")
        print("Created database: customs_trade_db")
    except Exception as e:
        print(f"Database may already exist: {e}")
    
    await conn.close()
    
    # 连接到新数据库并设置结构
    db_config['database'] = 'customs_trade_db'
    
    # 执行SQL脚本来创建表结构
    print("Creating tables...")
    conn = await asyncpg.connect(**db_config)
    
    # 读取并执行SQL脚本
    import os
    script_path = os.path.join(os.path.dirname(__file__), 'setup_customs_database.sql')
    with open(script_path, 'r', encoding='utf-8') as f:
        sql_script = f.read()
    
    # 分割SQL语句并执行
    statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]
    for statement in statements:
        if statement:
            try:
                await conn.execute(statement)
            except Exception as e:
                print(f"Error executing statement: {e}")
                print(f"Statement: {statement[:100]}...")
    
    await conn.close()
    print("Database structure created successfully")
    
    # 生成测试数据
    generator = CustomsDataGenerator(db_config)
    await generator.generate_all_data()

if __name__ == "__main__":
    asyncio.run(main())