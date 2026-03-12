"""周易预测模块 — 按日期得当日卦象（梅花易数时间起卦），供报告与 AI 参考。

起卦方法参考梅花易数：以公历日期转农历，固定取巳时（9–11 时，象征开盘）得本卦、互卦、变卦与体用。
算法与农历数据参考：https://github.com/muyen/meihua-yishu（CC BY-NC-SA 4.0）。纯娱乐与传统文化角度，不构成投资依据。
"""

from datetime import datetime, date
from typing import Tuple

from loguru import logger

# ---------------------------------------------------------------------------
# 六十四卦（周易序，0-based 与 ZHOUYI_64 一致）
# ---------------------------------------------------------------------------
ZHOUYI_64 = [
    ("乾", "乾为天", "刚健、主动、龙头"),
    ("坤", "坤为地", "柔顺、承载、稳健"),
    ("屯", "水雷屯", "初生、艰难中求进"),
    ("蒙", "山水蒙", "启蒙、待时而动"),
    ("需", "水天需", "等待、守正待时"),
    ("讼", "天水讼", "争讼、宜和解"),
    ("师", "地水师", "兴师、纪律与团结"),
    ("比", "水地比", "亲附、择善而从"),
    ("小畜", "风天小畜", "小有积蓄、蓄势"),
    ("履", "天泽履", "履行、慎行"),
    ("泰", "地天泰", "通泰、天地交泰"),
    ("否", "天地否", "闭塞、待转机"),
    ("同人", "天火同人", "同心、合作"),
    ("大有", "火天大有", "大有收获、丰盛"),
    ("谦", "地山谦", "谦逊、低调"),
    ("豫", "雷地豫", "愉悦、顺势而为"),
    ("随", "泽雷随", "随从、顺势"),
    ("蛊", "山风蛊", "整治、除弊"),
    ("临", "地泽临", "临近、督导"),
    ("观", "风地观", "观察、审时度势"),
    ("噬嗑", "火雷噬嗑", "咬合、除障碍"),
    ("贲", "山火贲", "文饰、适度"),
    ("剥", "山地剥", "剥落、守成为主"),
    ("复", "地雷复", "复归、见底回升"),
    ("无妄", "天雷无妄", "无妄、守正"),
    ("大畜", "山天大畜", "大蓄、厚积薄发"),
    ("颐", "山雷颐", "颐养、养正"),
    ("大过", "泽风大过", "大过、非常之时"),
    ("坎", "坎为水", "险陷、谨慎"),
    ("离", "离为火", "附丽、光明"),
    ("咸", "泽山咸", "感应、和合"),
    ("恒", "雷风恒", "恒久、持久"),
    ("遁", "天山遁", "退避、保存实力"),
    ("大壮", "雷天大壮", "大壮、勿过刚"),
    ("晋", "火地晋", "晋升、进取"),
    ("明夷", "地火明夷", "光明受伤、韬光养晦"),
    ("家人", "风火家人", "家庭、内部和谐"),
    ("睽", "火泽睽", "乖离、求同存异"),
    ("蹇", "水山蹇", "艰难、反身修德"),
    ("解", "雷水解", "解脱、缓解"),
    ("损", "山泽损", "减损、损下益上"),
    ("益", "风雷益", "增益、利有攸往"),
    ("夬", "泽天夬", "决断、果断"),
    ("姤", "天风姤", "相遇、防微杜渐"),
    ("萃", "泽地萃", "荟萃、聚集"),
    ("升", "地风升", "上升、顺势而升"),
    ("困", "泽水困", "困顿、守正待时"),
    ("井", "水风井", "井养、稳定供给"),
    ("革", "泽火革", "变革、除旧布新"),
    ("鼎", "火风鼎", "鼎立、稳重"),
    ("震", "震为雷", "震动、戒惧"),
    ("艮", "艮为山", "止息、适可而止"),
    ("渐", "风山渐", "渐进、循序渐进"),
    ("归妹", "雷泽归妹", "归嫁、慎终"),
    ("丰", "雷火丰", "丰大、持盈保泰"),
    ("旅", "火山旅", "行旅、谨慎"),
    ("巽", "巽为风", "入、顺从"),
    ("兑", "兑为泽", "悦、和悦"),
    ("涣", "风水涣", "涣散、聚散"),
    ("节", "水泽节", "节制、适度"),
    ("中孚", "风泽中孚", "诚信、守信"),
    ("小过", "雷山小过", "小过、慎行"),
    ("既济", "水火既济", "既济、守成"),
    ("未济", "火水未济", "未济、事未成待续"),
]

# ---------------------------------------------------------------------------
# 梅花易数：先天八卦数 1–8（余 0 当 8 坤）
# ---------------------------------------------------------------------------
BAGUA = {
    1: {"name": "乾", "binary": "111", "element": "金"},
    2: {"name": "兑", "binary": "011", "element": "金"},
    3: {"name": "离", "binary": "101", "element": "火"},
    4: {"name": "震", "binary": "001", "element": "木"},
    5: {"name": "巽", "binary": "110", "element": "木"},
    6: {"name": "坎", "binary": "010", "element": "水"},
    7: {"name": "艮", "binary": "100", "element": "土"},
    8: {"name": "坤", "binary": "000", "element": "土"},
}
BINARY_TO_GUA = {info["binary"]: num for num, info in BAGUA.items()}

# 上卦、下卦（先天数 1–8）→ 周易卦序 1–64（与 ZHOUYI_64 下标+1 一致）
UPPER_LOWER_TO_HEX_INDEX = {
    (1, 1): 1, (1, 2): 10, (1, 3): 13, (1, 4): 25, (1, 5): 44, (1, 6): 6, (1, 7): 33, (1, 8): 12,
    (2, 1): 43, (2, 2): 58, (2, 3): 49, (2, 4): 17, (2, 5): 28, (2, 6): 47, (2, 7): 31, (2, 8): 45,
    (3, 1): 14, (3, 2): 38, (3, 3): 30, (3, 4): 21, (3, 5): 50, (3, 6): 64, (3, 7): 56, (3, 8): 35,
    (4, 1): 34, (4, 2): 54, (4, 3): 55, (4, 4): 51, (4, 5): 32, (4, 6): 40, (4, 7): 62, (4, 8): 16,
    (5, 1): 9, (5, 2): 61, (5, 3): 37, (5, 4): 42, (5, 5): 57, (5, 6): 59, (5, 7): 53, (5, 8): 20,
    (6, 1): 5, (6, 2): 60, (6, 3): 63, (6, 4): 3, (6, 5): 48, (6, 6): 29, (6, 7): 39, (6, 8): 8,
    (7, 1): 26, (7, 2): 41, (7, 3): 22, (7, 4): 27, (7, 5): 18, (7, 6): 4, (7, 7): 52, (7, 8): 23,
    (8, 1): 11, (8, 2): 19, (8, 3): 36, (8, 4): 24, (8, 5): 46, (8, 6): 7, (8, 7): 15, (8, 8): 2,
}

# ---------------------------------------------------------------------------
# 农历数据（1900–2099，来源 meihua-yishu）
# bit16: 闰月是否大月; bit4–15: 12 月大小月; bit0–3: 闰月月份
# ---------------------------------------------------------------------------
LUNAR_YEAR_INFOS = [
    0x04bd8, 0x04ae0, 0x0a570, 0x054d5, 0x0d260, 0x0d950, 0x16554, 0x056a0, 0x09ad0, 0x055d2,
    0x04ae0, 0x0a5b6, 0x0a4d0, 0x0d250, 0x1d255, 0x0b540, 0x0d6a0, 0x0ada2, 0x095b0, 0x14977,
    0x04970, 0x0a4b0, 0x0b4b5, 0x06a50, 0x06d40, 0x1ab54, 0x02b60, 0x09570, 0x052f2, 0x04970,
    0x06566, 0x0d4a0, 0x0ea50, 0x06e95, 0x05ad0, 0x02b60, 0x186e3, 0x092e0, 0x1c8d7, 0x0c950,
    0x0d4a0, 0x1d8a6, 0x0b550, 0x056a0, 0x1a5b4, 0x025d0, 0x092d0, 0x0d2b2, 0x0a950, 0x0b557,
    0x06ca0, 0x0b550, 0x15355, 0x04da0, 0x0a5d0, 0x14573, 0x052d0, 0x0a9a8, 0x0e950, 0x06aa0,
    0x0aea6, 0x0ab50, 0x04b60, 0x0aae4, 0x0a570, 0x05260, 0x0f263, 0x0d950, 0x05b57, 0x056a0,
    0x096d0, 0x04dd5, 0x04ad0, 0x0a4d0, 0x0d4d4, 0x0d250, 0x0d558, 0x0b540, 0x0b5a0, 0x195a6,
    0x095b0, 0x049b0, 0x0a974, 0x0a4b0, 0x0b27a, 0x06a50, 0x06d40, 0x0af46, 0x0ab60, 0x09570,
    0x04af5, 0x04970, 0x064b0, 0x074a3, 0x0ea50, 0x06b58, 0x05ac0, 0x0ab60, 0x096d5, 0x092e0,
    0x0c960, 0x0d954, 0x0d4a0, 0x0da50, 0x07552, 0x056a0, 0x0abb7, 0x025d0, 0x092d0, 0x0cab5,
    0x0a950, 0x0b4a0, 0x0baa4, 0x0ad50, 0x055d9, 0x04ba0, 0x0a5b0, 0x15176, 0x052b0, 0x0a930,
    0x07954, 0x06aa0, 0x0ad50, 0x05b52, 0x04b60, 0x0a6e6, 0x0a4e0, 0x0d260, 0x0ea65, 0x0d530,
    0x05aa0, 0x076a3, 0x096d0, 0x04afb, 0x04ad0, 0x0a4d0, 0x1d0b6, 0x0d250, 0x0d520, 0x0dd45,
    0x0b5a0, 0x056d0, 0x055b2, 0x049b0, 0x0a577, 0x0a4b0, 0x0aa50, 0x1b255, 0x06d20, 0x0ada0,
    0x14b63, 0x09370, 0x049f8, 0x04970, 0x064b0, 0x168a6, 0x0ea50, 0x06aa0, 0x1a6c4, 0x0aae0,
    0x092e0, 0x0d2e3, 0x0c960, 0x0d557, 0x0d4a0, 0x0da50, 0x05d55, 0x056a0, 0x0a6d0, 0x055d4,
    0x052d0, 0x0a9b8, 0x0a950, 0x0b4a0, 0x0b6a6, 0x0ad50, 0x055a0, 0x0aba4, 0x0a5b0, 0x052b0,
    0x0b273, 0x06930, 0x07337, 0x06aa0, 0x0ad50, 0x14b55, 0x04b60, 0x0a570, 0x054e4, 0x0d160,
    0x0e968, 0x0d520, 0x0daa0, 0x16aa6, 0x056d0, 0x04ae0, 0x0a9d4, 0x0a2d0, 0x0d150, 0x0f252,
]
LUNAR_EPOCH = date(1900, 1, 31)


def _lunar_year_days(year_info: int) -> int:
    days = 29 * 12
    leap = year_info & 0xF
    if leap:
        days += 29
    if (year_info >> 16) & 1:
        days += 1
    for m in range(1, 13):
        if (year_info >> (16 - m)) & 1:
            days += 1
    return days


def _lunar_month_days(year_info: int, month: int, is_leap: bool) -> int:
    if is_leap:
        return 30 if (year_info >> 16) & 1 else 29
    return 30 if (year_info >> (16 - month)) & 1 else 29


def _gregorian_to_lunar(year: int, month: int, day: int) -> Tuple[int, int, int, bool]:
    """公历 → 农历 (年, 月, 日, 是否闰月)。支持 1900–2099。"""
    if year < 1900 or year > 2099:
        raise ValueError(f"年份 {year} 超出范围 (1900–2099)")
    target = date(year, month, day)
    offset = (target - LUNAR_EPOCH).days
    if offset < 0:
        raise ValueError("日期早于 1900-01-31")
    idx = 0
    lunar_year = 1900
    while idx < len(LUNAR_YEAR_INFOS):
        info = LUNAR_YEAR_INFOS[idx]
        y_days = _lunar_year_days(info)
        if offset < y_days:
            break
        offset -= y_days
        lunar_year += 1
        idx += 1
    if idx >= len(LUNAR_YEAR_INFOS):
        raise ValueError("日期超出支持范围")
    info = LUNAR_YEAR_INFOS[idx]
    leap_month = info & 0xF
    for m in range(1, 13):
        days = _lunar_month_days(info, m, False)
        if offset < days:
            return (lunar_year, m, offset + 1, False)
        offset -= days
        if m == leap_month:
            days = _lunar_month_days(info, m, True)
            if offset < days:
                return (lunar_year, m, offset + 1, True)
            offset -= days
    raise ValueError("农历计算错误")


def _year_dizhi_num(lunar_year: int) -> int:
    """农历年地支序数 1–12（1900 庚子=子1）。"""
    n = ((lunar_year - 1900) % 12) + 1
    return 1 if n == 13 else n


def _num_to_gua(n: int) -> int:
    """数 mod 8 得卦数，余 0 当 8。"""
    r = n % 8
    return 8 if r == 0 else r


def _num_to_yao(n: int) -> int:
    """数 mod 6 得动爻 1–6，余 0 当 6。"""
    r = n % 6
    return 6 if r == 0 else r


def _hexagram_binary(upper: int, lower: int) -> str:
    return BAGUA[upper]["binary"] + BAGUA[lower]["binary"]


def _apply_change(binary: str, yao_pos: int) -> str:
    """动爻从下往上 1–6，取反。"""
    i = 6 - yao_pos
    s = list(binary)
    s[i] = "0" if s[i] == "1" else "1"
    return "".join(s)


def _binary_to_upper_lower(binary: str) -> Tuple[int, int]:
    return BINARY_TO_GUA[binary[:3]], BINARY_TO_GUA[binary[3:]]


def _hu_gua(upper: int, lower: int) -> Tuple[int, int]:
    """互卦：本卦 2–3–4 爻为下互，3–4–5 爻为上互。"""
    b = _hexagram_binary(upper, lower)
    hu_lower = BINARY_TO_GUA[b[1:4]]
    hu_upper = BINARY_TO_GUA[b[2:5]]
    return hu_upper, hu_lower


def _ti_yong_relation(ti_el: str, yong_el: str) -> str:
    """体用五行生克：用生体大吉，体克用小吉，比和吉，体生用泄，用克体凶。"""
    sheng = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
    ke = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
    if ti_el == yong_el:
        return "体用比和（吉）"
    if sheng.get(yong_el) == ti_el:
        return "用生体（大吉）"
    if sheng.get(ti_el) == yong_el:
        return "体生用（泄）"
    if ke.get(ti_el) == yong_el:
        return "体克用（小吉）"
    if ke.get(yong_el) == ti_el:
        return "用克体（凶）"
    return "体用关系"


def get_daily_hexagram(trade_date: str = None) -> dict:
    """按梅花易数时间起卦得当日卦象（公历转农历，固定巳时=6）。

    每日一卦由日期唯一确定。返回本卦信息及互卦、变卦、体用等，兼容原有 name/full_name/image/index。
    """
    if trade_date is None:
        trade_date = datetime.now().strftime("%Y-%m-%d")
    try:
        dt = datetime.strptime(trade_date[:10], "%Y-%m-%d")
    except ValueError:
        dt = datetime.now()
    y, m, d = dt.year, dt.month, dt.day
    ly, lm, ld, is_leap = _gregorian_to_lunar(y, m, d)
    # 固定巳时（9–11 时）数=6，象征开盘
    shichen_num = 6
    year_num = _year_dizhi_num(ly)
    upper_sum = year_num + lm + ld
    lower_sum = upper_sum + shichen_num
    upper_gua = _num_to_gua(upper_sum)
    lower_gua = _num_to_gua(lower_sum)
    dong_yao = _num_to_yao(lower_sum)
    # 本卦
    hex_index = UPPER_LOWER_TO_HEX_INDEX.get((upper_gua, lower_gua), 1)
    idx = hex_index - 1
    name, full_name, image = ZHOUYI_64[idx]
    # 体用：动爻在上卦(4–6)则上卦为用、下卦为体；动爻在下卦(1–3)则下卦为用、上卦为体
    if dong_yao > 3:
        ti_gua, yong_gua = lower_gua, upper_gua
    else:
        ti_gua, yong_gua = upper_gua, lower_gua
    ti_el = BAGUA[ti_gua]["element"]
    yong_el = BAGUA[yong_gua]["element"]
    ti_yong = _ti_yong_relation(ti_el, yong_el)
    # 互卦
    hu_upper, hu_lower = _hu_gua(upper_gua, lower_gua)
    hu_hex = UPPER_LOWER_TO_HEX_INDEX.get((hu_upper, hu_lower))
    hu_name = ZHOUYI_64[hu_hex - 1][0] if hu_hex else ""
    # 变卦
    bin_ben = _hexagram_binary(upper_gua, lower_gua)
    bin_bian = _apply_change(bin_ben, dong_yao)
    bu, bl = _binary_to_upper_lower(bin_bian)
    bian_hex = UPPER_LOWER_TO_HEX_INDEX.get((bu, bl))
    bian_name = ZHOUYI_64[bian_hex - 1][0] if bian_hex else ""
    lunar_str = f"{ly}年{'闰' if is_leap else ''}{lm}月{ld}日"
    logger.info(
        f"周易起卦: 公历 {trade_date[:10]} → 农历 {lunar_str} | "
        f"本卦 {full_name}（{name}卦）动爻第{dong_yao}爻 | {ti_yong} | 互卦 {hu_name or '-'} 变卦 {bian_name or '-'}"
    )
    return {
        "name": name,
        "full_name": full_name,
        "image": image,
        "index": idx,
        "dong_yao": dong_yao,
        "hu_gua_name": hu_name,
        "bian_gua_name": bian_name,
        "ti_yong": ti_yong,
        "lunar": lunar_str,
    }


def zhouyi_summary_for_ai(trade_date: str = None) -> str:
    """返回给 AI 的周易摘要（含本卦、体用、变卦）。"""
    h = get_daily_hexagram(trade_date)
    s = f"今日卦象：{h['full_name']}（{h['name']}卦），象意：{h['image']}。"
    if h.get("ti_yong"):
        s += f" 体用：{h['ti_yong']}"
    if h.get("bian_gua_name"):
        s += f"；变卦：{h['bian_gua_name']}。"
    else:
        s += "。"
    logger.debug(f"周易摘要(供AI): {s[:80]}...")
    return s
