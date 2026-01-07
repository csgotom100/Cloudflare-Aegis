import json
import os
import sys
import time

FILE_JSON = "ip_pool.json"
# 永久封禁名单：一旦被举报且在此名单，直接抹除
HARD_BLACKLIST = {"1.0.1.1", "1.2.1.1", "1.1.1.1", "1.0.0.1"}

def apply_penalty(ip):
    if not os.path.exists(FILE_JSON): return

    with open(FILE_JSON, 'r', encoding='utf-8') as f:
        db = json.load(f)

    pool_key = 'pool' if 'pool' in db else 'ips'
    
    if ip in db[pool_key] or ip in HARD_BLACKLIST:
        print(f"🎯 处理恶意 IP: {ip}")
        
        # 字典结构删除
        if isinstance(db[pool_key], dict):
            db[pool_key].pop(ip, None) 
        # 列表结构删除 (兼容)
        elif isinstance(db[pool_key], list) and ip in db[pool_key]:
            db[pool_key].remove(ip)

        db['last_update'] = f"Manual Purge: {ip}"
        
        with open(FILE_JSON, 'w', encoding='utf-8') as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
        print(f"✅ {ip} 已从数据库永久抹除")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        apply_penalty(sys.argv[1].strip())
