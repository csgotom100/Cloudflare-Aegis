import json
import os
import sys

FILE_JSON = "ip_pool.json"

def apply_penalty(ip):
    if not os.path.exists(FILE_JSON):
        print("❌ 数据库文件不存在")
        return

    with open(FILE_JSON, 'r', encoding='utf-8') as f:
        db = json.load(f)

    # --- 修正点：适配新的键名 'ips' ---
    # 如果你的 JSON 里用的是 'ips'，这里就改成 'ips'
    pool_key = 'ips' if 'ips' in db else 'pool'
    
    if ip in db[pool_key]:
        print(f"🎯 正在从弹药库移除坏 IP: {ip}")
        db[pool_key].remove(ip)
        db['last_update'] = "Reported Cleanup"
        
        with open(FILE_JSON, 'w', encoding='utf-8') as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
        print(f"✅ 已完成更新，该 IP 已被踢出库。")
    else:
        print(f"ℹ️ IP {ip} 不在当前活跃库中，无需处理。")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        apply_penalty(sys.argv[1])
    else:
        print("⚠️ 未提供 IP 参数")
