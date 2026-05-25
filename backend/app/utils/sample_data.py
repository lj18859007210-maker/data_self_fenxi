import polars as pl
import numpy as np
from pathlib import Path


def generate_sales_data(n_rows: int = 10000) -> pl.DataFrame:
    """Generate sample sales dataset."""
    np.random.seed(42)
    cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "南京"]
    categories = ["电子产品", "服装", "食品", "家居", "图书", "运动"]
    products = {
        "电子产品": ["iPhone 15", "MacBook Pro", "AirPods", "iPad Air", "Apple Watch"],
        "服装": ["运动鞋", "羽绒服", "T恤", "牛仔裤", "连衣裙"],
        "食品": ["巧克力", "坚果礼盒", "咖啡豆", "有机茶叶", "进口红酒"],
        "家居": ["台灯", "抱枕", "收纳盒", "地毯", "挂画"],
        "图书": ["Python编程", "数据科学", "设计模式", "算法导论", "经济学原理"],
        "运动": ["瑜伽垫", "哑铃", "跑步机", "跳绳", "泳镜"],
    }

    data = {
        "订单ID": [f"ORD{i:06d}" for i in range(n_rows)],
        "订单金额": np.round(np.random.lognormal(mean=5.5, sigma=0.8, size=n_rows), 2),
        "城市": np.random.choice(cities, size=n_rows),
        "商品类别": np.random.choice(categories, size=n_rows),
    }

    df = pl.DataFrame(data)

    # Fill product names based on category
    products_list = []
    for cat in df["商品类别"].to_list():
        products_list.append(np.random.choice(products[cat]))
    df = df.with_columns(pl.Series("商品名称", products_list))

    # Add datetime
    start = np.datetime64("2024-01-01")
    end = np.datetime64("2024-12-31")
    timestamps = start + (end - start) * np.random.random(n_rows)
    df = df.with_columns(pl.Series("下单时间", [str(t)[:19] for t in timestamps]))

    # Add boolean field
    df = df.with_columns(pl.Series("是否退货", np.random.choice([True, False], size=n_rows, p=[0.15, 0.85])))

    # Add some missing values
    missing_idx = np.random.choice(n_rows, size=int(n_rows * 0.02), replace=False)
    amounts = df["订单金额"].to_list()
    for idx in missing_idx:
        amounts[idx] = None
    df = df.with_columns(pl.Series("订单金额", amounts))

    return df


def get_sample_datasets() -> dict:
    return {
        "sales_data": {
            "name": "销售数据",
            "description": "包含订单金额、城市分布、商品类别等多维度的销售记录",
            "rows": 10000,
        }
    }


def save_sample_data(dir_path: Path) -> str:
    """Generate and save sample data, return path."""
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / "sales_data.csv"
    if not file_path.exists():
        df = generate_sales_data()
        df.write_csv(file_path)
    return str(file_path)
