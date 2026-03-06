from neo4j import GraphDatabase
import re

# 🔐 连接配置（请按实际修改）
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "Admin123456")

driver = GraphDatabase.driver(URI, auth=AUTH)

def safe_run(session, cypher: str, desc: str = ""):
    try:
        session.run(cypher)
        print(f"✅ {desc or '执行成功'}")
    except Exception as e:
        # 忽略“已存在”类错误（如 CREATE (:Class {...}) 重复）
        if "already exists" in str(e) or "UniqueConstraintViolation" in str(e):
            print(f"⚠️  {desc or '已存在，跳过'}")
        else:
            print(f"❌ {desc or '执行失败'}: {e}")

def load_ontology_cypher(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 按分号分割（保留注释和换行）
    statements = [s.strip() for s in re.split(r';\s*(?=\n|$)', content) if s.strip()]

    with driver.session() as session:
        for i, stmt in enumerate(statements, 1):
            # 跳过空行和纯注释行
            if not stmt or stmt.startswith('//') or stmt.startswith('/*'):
                continue
            # 提取第一行作为描述（用于日志）
            desc_line = stmt.split('\n')[0].strip().replace('//', '').strip()
            safe_run(session, stmt, f"[{i}] {desc_line[:40]}...")

if __name__ == "__main__":
    print("🚀 开始加载路侧停车本体定义...")
    load_ontology_cypher("parking_rag_ontology.cypher")  # ← 保存你上面的脚本为这个文件名
    print("\n🎉 本体加载完成！")
    driver.close()