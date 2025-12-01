"""
创建完整的测试环境数据
"""
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent


def setup_test_data():
    """创建测试所需的所有数据"""
    
    print("=" * 60)
    print("🔧 创建测试环境数据")
    print("=" * 60)
    
    # ==========================================
    # 1. 创建世界目录结构
    # ==========================================
    print("\n📁 1. 创建世界目录结构...")
    
    world_dir = PROJECT_ROOT / "data" / "worlds" / "江城市"
    characters_dir = world_dir / "characters"
    characters_dir.mkdir(parents=True, exist_ok=True)
    print(f"   ✅ {characters_dir}")
    
    # ==========================================
    # 2. 创建角色卡
    # ==========================================
    print("\n📁 2. 创建角色卡...")
    
    # 林晨 - 软件工程师
    npc_001 = {
        "id": "npc_001",
        "name": "林晨",
        "gender": "男",
        "age": "28岁",
        "importance": 85.0,
        "traits": [
            "软件工程师",
            "技术宅",
            "正义感强",
            "有些社恐"
        ],
        "behavior_rules": [
            "遇到技术问题会兴奋地深入研究",
            "面对陌生人时会紧张，说话结巴",
            "发现不公正的事情会挺身而出",
            "喜欢用技术手段解决问题"
        ],
        "relationship_matrix": {
            "user": {
                "address_as": "朋友",
                "attitude": "友好但保持距离"
            },
            "npc_002": {
                "address_as": "晴雨",
                "attitude": "信任，欣赏她的勇敢"
            }
        },
        "possessions": [
            "笔记本电脑",
            "智能手机",
            "U盘（存有关键证据）"
        ],
        "current_appearance": "瘦削的年轻男子，戴着黑框眼镜，穿着格子衬衫和牛仔裤，眼神疲惫但专注",
        "voice_samples": [
            "这个数据异常太明显了，肯定有问题...",
            "等等，让我看看代码...",
            "我...我不太擅长和人打交道，但这件事我必须管"
        ]
    }
    
    # 苏晴雨 - 记者
    npc_002 = {
        "id": "npc_002",
        "name": "苏晴雨",
        "gender": "女",
        "age": "26岁",
        "importance": 85.0,
        "traits": [
            "调查记者",
            "果断勇敢",
            "观察力强",
            "有正义感"
        ],
        "behavior_rules": [
            "对任何线索都保持警觉",
            "说话直接，不喜欢绕弯子",
            "面对危险时冷静应对",
            "为了真相可以冒险"
        ],
        "relationship_matrix": {
            "user": {
                "address_as": "你",
                "attitude": "保持职业警觉，但愿意合作"
            },
            "npc_001": {
                "address_as": "林晨",
                "attitude": "信任，感谢他的技术支持"
            }
        },
        "possessions": [
            "录音笔",
            "相机",
            "采访笔记本"
        ],
        "current_appearance": "长发微乱的年轻女子，穿着休闲外套和牛仔裤，眼神锐利，神态冷静",
        "voice_samples": [
            "我追踪这条线索已经很久了",
            "你有什么证据？说出来",
            "真相就在那里，我们必须揭露它"
        ]
    }
    
    # 保存角色卡
    with open(characters_dir / "npc_001.json", "w", encoding="utf-8") as f:
        json.dump(npc_001, f, ensure_ascii=False, indent=2)
    print(f"   ✅ npc_001.json (林晨)")
    
    with open(characters_dir / "npc_002.json", "w", encoding="utf-8") as f:
        json.dump(npc_002, f, ensure_ascii=False, indent=2)
    print(f"   ✅ npc_002.json (苏晴雨)")
    
    # ==========================================
    # 3. 创建运行时目录结构
    # ==========================================
    print("\n📁 3. 创建运行时目录...")
    
    runtime_dir = PROJECT_ROOT / "data" / "runtime" / "江城市_20251128_183246"
    
    plot_dir = runtime_dir / "plot"
    ws_dir = runtime_dir / "ws"
    npc_dir = runtime_dir / "npc"
    memory_dir = npc_dir / "memory"
    history_dir = npc_dir / "history"
    
    for d in [plot_dir, ws_dir, npc_dir, memory_dir, history_dir]:
        d.mkdir(parents=True, exist_ok=True)
        print(f"   ✅ {d.relative_to(PROJECT_ROOT)}")
    
    # ==========================================
    # 4. 创建 current_scene.json
    # ==========================================
    print("\n📁 4. 创建场景配置...")
    
    current_scene = {
        "scene_id": "scene_001",
        "location": "市中心咖啡馆",
        "time": "上午10:30",
        "weather": "晴朗",
        "atmosphere": "繁忙的都市氛围，咖啡香弥漫",
        "characters": [
            {
                "id": "npc_001",
                "name": "林晨",
                "status": "在场",
                "first_appearance": True,
                "current_activity": "在角落的座位上专注查看笔记本电脑"
            },
            {
                "id": "npc_002",
                "name": "苏晴雨",
                "status": "在场",
                "first_appearance": True,
                "current_activity": "坐在林晨对面，一边喝咖啡一边观察周围"
            }
        ],
        "background_npcs": [
            "几位正在工作的白领",
            "一对情侣在窗边聊天",
            "服务员来回走动"
        ]
    }
    
    with open(plot_dir / "current_scene.json", "w", encoding="utf-8") as f:
        json.dump(current_scene, f, ensure_ascii=False, indent=2)
    print(f"   ✅ current_scene.json")
    
    # ==========================================
    # 5. 创建 current_script.json
    # ==========================================
    print("\n📁 5. 创建剧本...")
    
    current_script = {
        "script_id": "script_001",
        "act": 1,
        "scene": 1,
        "title": "危机初现",
        "summary": "林晨在咖啡馆里发现了鸿图科技的异常数据，正好遇到了也在追查此事的记者苏晴雨。两人决定合作揭露真相。",
        "objectives": [
            "林晨向苏晴雨展示他发现的证据",
            "苏晴雨分享她收集的线索",
            "两人决定合作"
        ],
        "expected_outcome": "双方建立信任，达成合作共识",
        "tension_level": "中等",
        "notes": "这是故事的开端，需要建立角色之间的联系"
    }
    
    with open(plot_dir / "current_script.json", "w", encoding="utf-8") as f:
        json.dump(current_script, f, ensure_ascii=False, indent=2)
    print(f"   ✅ current_script.json")
    
    # ==========================================
    # 6. 创建 world_state.json
    # ==========================================
    print("\n📁 6. 创建世界状态...")
    
    world_state = {
        "world_id": "江城市",
        "current_date": "2025年11月28日",
        "current_time": "上午10:30",
        "weather": {
            "condition": "晴朗",
            "temperature": "22°C"
        },
        "global_events": [
            "鸿图科技最近因AI服务获得大量用户",
            "有传言称该公司存在数据安全问题",
            "城市正在举办科技创新周"
        ],
        "timeline": {
            "minutes_elapsed": 20,
            "description": "故事开始后过去了20分钟"
        }
    }
    
    with open(ws_dir / "world_state.json", "w", encoding="utf-8") as f:
        json.dump(world_state, f, ensure_ascii=False, indent=2)
    print(f"   ✅ world_state.json")
    
    # ==========================================
    # 完成
    # ==========================================
    print("\n" + "=" * 60)
    print("✅ 测试环境数据创建完成！")
    print("=" * 60)
    
    print("\n📋 创建的目录结构:")
    print(f"""
data/
├── worlds/
│   └── 江城市/
│       └── characters/
│           ├── npc_001.json (林晨)
│           └── npc_002.json (苏晴雨)
└── runtime/
    └── 江城市_20251128_183246/
        ├── plot/
        │   ├── current_scene.json
        │   └── current_script.json
        ├── ws/
        │   └── world_state.json
        └── npc/
            ├── memory/
            └── history/
""")
    
    return True


if __name__ == "__main__":
    setup_test_data()

