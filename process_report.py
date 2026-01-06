import json
import os
import sys
import time
from datetime import datetime  # 补齐这个关键导入
from github import Github, Auth

# --- 自定义禁闭策略 ---
BAN_THRESHOLD = 1         # 反馈 1 次就拉黑（测试完可改回 5）
BAN_SECONDS = 24 * 3600   # 拉黑时长 (24小时)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = os.getenv("GITHUB_REPOSITORY")
FILE_JSON = "ip_pool.json"
FILE_TXT = "ips_txt_view.txt"

def apply_penalty(ip):
    auth = Auth.Token(GITHUB_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo(REPO_NAME)
    
    # 1. 获取库文件
    contents = repo.get_contents(FILE_JSON)
    db = json.loads(contents.decoded_content.decode())
    
    if ip in db['pool']:
        # 2. 增加反馈计数
        db['pool'][ip]['fail_count'] = db['pool'][ip].get('fail_count', 0) + 1
        count = db['pool'][ip]['fail_count']
        
        # 3. 检查是否触发禁闭
        if count >= BAN_THRESHOLD:
            db['pool'][ip]['ban_until'] = int(time.time()) + BAN_SECONDS
            db['pool'][ip]['score'] = 0
            msg = f"🚫 IP {ip} 反馈已达标 ({count}次)，正式关禁闭 24 小时。"
        else:
            msg = f"⚠️ IP {ip} 当前累计反馈: {count}/{BAN_THRESHOLD}"
        
        # 4. 【实时同步】重新生成 TXT 内容 (排除禁闭 IP)
        active_ips = [i for i, info in db['pool'].items() if info.get('ban_until', 0) == 0]
        update_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        txt_content = f"# 活跃弹药库 (更新: {update_time})\n# 总活跃数: {len(active_ips)}\n\n"
        txt_content += "\n".join(sorted(active_ips))

        # 5. 提交 JSON 更新
        repo.update_file(contents.path, f"Penalty: {ip}", json.dumps(db, indent=2), contents.sha)
        
        # 6. 提交 TXT 更新
        try:
            txt_file = repo.get_contents(FILE_TXT)
            repo.update_file(FILE_TXT, "Sync View after Feedback", txt_content, txt_file.sha)
        except:
            repo.create_file(FILE_TXT, "Init View", txt_content)
            
        print(msg)
    else:
        print(f"IP {ip} 不在库中。")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        apply_penalty(sys.argv[1])
