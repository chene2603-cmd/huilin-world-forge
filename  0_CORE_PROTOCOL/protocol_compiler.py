"""
慧凌世界核心协议层 - 协议编译器 v0.1
负责加载、编译、校验世界构成规则（地形、生态、资源、文明约束）。
协议以 JSON 形式定义，编译器将其转为强类型对象供下游模块使用。
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path

# ---------- 协议数据结构 ----------
@dataclass
class HeightRule:
    """地形高度规则"""
    min_height: float        # 最低高度 (米)
    max_height: float        # 最高高度 (米)
    coverage: float          # 占世界面积比 (0~1)
    terrain_types: List[str] # 此地高度常见地形 (如 "plain", "mountain")

@dataclass
class BiomeRule:
    """生物群系规则"""
    name: str
    temperature_range: tuple  # (min, max) 摄氏度
    humidity_range: tuple     # (min, max) 百分比
    allowed_terrains: List[str]
    vegetation_density: float # 0~1

@dataclass
class ResourceRule:
    """资源分布规则"""
    name: str
    biome_affinity: List[str] # 倾向出现的生物群系
    rarity: float             # 0~1，越小越稀有
    min_depth: float          # 最小生成深度，负数表示地表

@dataclass
class CivilizationConstraint:
    """文明生成约束"""
    max_city_radius: float
    preferred_terrains: List[str]
    forbidden_biomes: List[str]
    tech_level: int           # 1-10

@dataclass
class WorldProtocol:
    """完整的世界协议"""
    world_name: str
    seed: int
    map_size: tuple           # (width, height) 公里
    height_rules: List[HeightRule]
    biomes: List[BiomeRule]
    resources: List[ResourceRule]
    civilization: CivilizationConstraint

# ---------- 编译器 ----------
class ProtocolCompiler:
    """编译和校验世界协议"""

    @staticmethod
    def load_from_json(filepath: str) -> WorldProtocol:
        """从 JSON 文件加载并编译为 WorldProtocol 对象"""
        with open(filepath, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        return ProtocolCompiler.compile(raw)

    @staticmethod
    def compile(raw: dict) -> WorldProtocol:
        """对原始字典进行校验并转换为强类型协议"""
        # 校验必填字段
        required_top = ['world_name', 'seed', 'map_size', 'height_rules', 'biomes', 'resources', 'civilization']
        for key in required_top:
            if key not in raw:
                raise ValueError(f"协议缺少必要字段: {key}")

        # 编译高度规则
        height_rules = []
        for hr in raw['height_rules']:
            height_rules.append(HeightRule(
                min_height=hr['min_height'],
                max_height=hr['max_height'],
                coverage=hr['coverage'],
                terrain_types=hr['terrain_types']
            ))
        # 校验 coverage 总和约为 1
        total_coverage = sum(h.coverage for h in height_rules)
        if not 0.99 <= total_coverage <= 1.01:
            raise ValueError(f"高度规则 coverage 总和应为 1.0，当前: {total_coverage}")

        # 编译生物群系
        biomes = []
        for br in raw['biomes']:
            biomes.append(BiomeRule(
                name=br['name'],
                temperature_range=tuple(br['temperature_range']),
                humidity_range=tuple(br['humidity_range']),
                allowed_terrains=br['allowed_terrains'],
                vegetation_density=br['vegetation_density']
            ))

        # 编译资源规则
        resources = []
        for rr in raw['resources']:
            resources.append(ResourceRule(
                name=rr['name'],
                biome_affinity=rr['biome_affinity'],
                rarity=rr['rarity'],
                min_depth=rr['min_depth']
            ))

        # 编译文明约束
        civ_raw = raw['civilization']
        civilization = CivilizationConstraint(
            max_city_radius=civ_raw['max_city_radius'],
            preferred_terrains=civ_raw['preferred_terrains'],
            forbidden_biomes=civ_raw['forbidden_biomes'],
            tech_level=civ_raw['tech_level']
        )

        return WorldProtocol(
            world_name=raw['world_name'],
            seed=raw['seed'],
            map_size=tuple(raw['map_size']),
            height_rules=height_rules,
            biomes=biomes,
            resources=resources,
            civilization=civilization
        )

    @staticmethod
    def validate_protocol(protocol: WorldProtocol) -> List[str]:
        """深度校验协议内部逻辑一致性，返回问题列表"""
        warnings = []
        terrain_types = set()
        for hr in protocol.height_rules:
            terrain_types.update(hr.terrain_types)

        # 检查生物群系引用的地形是否已定义
        for biome in protocol.biomes:
            for t in biome.allowed_terrains:
                if t not in terrain_types:
                    warnings.append(f"生物群系 '{biome.name}' 引用了未定义地形: '{t}'")

        # 检查资源引用的生物群系
        biome_names = {b.name for b in protocol.biomes}
        for res in protocol.resources:
            for b in res.biome_affinity:
                if b not in biome_names:
                    warnings.append(f"资源 '{res.name}' 引用了未定义生物群系: '{b}'")

        # 检查文明约束地形/群系
        for t in protocol.civilization.preferred_terrains:
            if t not in terrain_types:
                warnings.append(f"文明偏好地形未定义: '{t}'")
        for b in protocol.civilization.forbidden_biomes:
            if b not in biome_names:
                warnings.append(f"文明禁地生物群系未定义: '{b}'")

        return warnings

# ---------- 简易测试入口 ----------
if __name__ == "__main__":
    # 准备一份示例协议文件路径（你也可以直接传入字典）
    example_json = Path(__file__).parent / "example_world_protocol.json"
    if example_json.exists():
        protocol = ProtocolCompiler.load_from_json(str(example_json))
        print(f"✅ 协议编译成功: {protocol.world_name}")
        print(f"   地图尺寸: {protocol.map_size} km")
        print(f"   高度带数量: {len(protocol.height_rules)}")
        print(f"   生物群系数量: {len(protocol.biomes)}")
        print(f"   资源种类: {len(protocol.resources)}")
        print(f"   文明等级: {protocol.civilization.tech_level}")

        warnings = ProtocolCompiler.validate_protocol(protocol)
        if warnings:
            print("\n⚠️ 校验警告:")
            for w in warnings:
                print(f"   - {w}")
        else:
            print("✅ 协议逻辑校验通过")
    else:
        print(f"示例协议文件不存在: {example_json}")
        print("请创建一个 example_world_protocol.json 文件。")