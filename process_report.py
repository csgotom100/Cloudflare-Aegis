import json
import os
import sys
import time
from github import Github, Auth

# --- 自定义禁闭策略 ---
BAN_THRESHOLD = 5         # 被反馈 5 次就拉黑
BAN_SECONDS = 24 * 3600   # 拉黑时长 (24小时)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = os.getenv("GITHUB_REPOSITORY")
FILE_JSON = "ip_pool.json"

def apply_penalty(ip):
    auth = Auth.Token(GITHUB_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo(REPO_NAME)
    
    contents = repo.get_contents(FILE_JSON)
    db = json.loads(contents.decoded_content.decode())
    
    if ip in db['pool']:
        # 增加反馈计数
        db['pool'][ip]['fail_count'] = db['pool'][ip].get('fail_count', 0) + 1
        count = db['pool'][ip]['fail_count']
        
        # 检查是否触发禁闭
        if count >= BAN_THRESHOLD:
            db['pool'][ip]['ban_until'] = int(time.time()) + BAN_SECONDS
            db['pool'][ip]['score'] = 0
            msg = f"🚫 IP {ip} 反馈过高 ({count}次)，已关禁闭 24 小时。"
        else:
            msg = f"⚠️ IP {ip} 被反馈一次，当前累计: {count}/{BAN_THRESHOLD}"
        
        print(msg)
        repo.update_file(contents.path, f"Feedback: {ip}", json.dumps(db, indent=2), contents.sha)
    else:
        print(f"IP {ip} 不在库中，忽略。")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        apply_penalty(sys.argv[1])
