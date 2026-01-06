系统使用手册
分发端：你的客户端/代理服务器只需请求 https://raw.githubusercontent.com/用户名/仓库名/main/ips_txt_view.txt 即可获得最优质的 IP。

反馈端：当代理服务器发现某个 IP 连续几次握手失败或速度极慢时，自动调用 GitHub API 创建一个 Issue。

API 调用示例（给你的代理服务器用）：

Bash

curl -X POST -H "Authorization: token <你的TOKEN>" \
     -d '{"title":"FEEDBACK: 1.2.3.4"}' \
     https://api.github.com/repos/用户名/仓库名/issues
结果：GitHub 收到反馈后会自动在 ip_pool.json 里累计次数，达到 5 次后，下次 ips_txt_view.txt 生成时就会彻底消失。24 小时后，aegis_collector.py 运行时会自动将其“刑满释放”。


我们来编写最后一块拼图：VPS 自动换弹脚本。

这个脚本逻辑很硬核：它会定时监控当前 IP 是否通畅。如果发现断流，它会执行“弹药更替”——先向 GitHub 举报这个坏 IP（送它进禁闭室），然后从 ips_txt_view.txt 抓取一个最高分的新 IP 并更新你的代理配置。

第一步：准备举报工具
在 VPS 上，你需要安装 jq 来处理 JSON，确保你能通过命令行发 Issue。

Bash

sudo apt update && sudo apt install -y jq curl
第二步：编写 VPS 监控脚本 aegis_monitor.sh
在你的 VPS 根目录下创建该文件。

注意：你需要填入你的 GitHub Token、用户名/仓库名，以及你代理工具修改 IP 的具体命令。

Bash

#!/bin/bash

# --- 配置区 ---
GH_TOKEN="你的_GITHUB_TOKEN"
REPO="你的用户名/Cloudflare-Aegis"
RAW_URL="https://raw.githubusercontent.com/$REPO/main/ips_txt_view.txt"

# 你当前正在使用的 IP 存储位置（脚本会自动维护这个文件）
CURRENT_IP_FILE="/root/current_cf_ip.txt"
# 代理配置文件的路径（例如你的 YAML 或 JSON 配置）
CONFIG_PATH="/etc/v2ray/config.json" 

# --- 1. 检测当前网络 ---
# 尝试访问 Google 判断是否断流
check_status() {
    status_code=$(curl -I -m 5 -o /dev/null -s -w %{http_code} https://www.google.com)
    if [ "$status_code" -eq 200 ]; then
        return 0 # 正常
    else
        return 1 # 断流
    fi
}

# --- 2. 举报坏 IP ---
report_bad_ip() {
    local bad_ip=$1
    echo "🚨 检测到断流，正在举报坏 IP: $bad_ip"
    curl -s -X POST -H "Authorization: token $GH_TOKEN" \
         -d "{\"title\":\"FEEDBACK: $bad_ip\"}" \
         "https://api.github.com/repos/$REPO/issues" > /dev/null
}

# --- 3. 抓取新弹药 ---
get_new_ip() {
    echo "🔄 正在从弹药库抓取新 IP..."
    # 随机抓取文本中的一个 IP (排除掉注释行)
    new_ip=$(curl -s $RAW_URL | grep -v "#" | shuf -n 1)
    echo $new_ip
}

# --- 主逻辑 ---
if check_status; then
    echo "$(date): 网络通畅，无需行动。"
else
    echo "$(date): 网络中断！启动 Aegis 应急预案..."
    
    # 获取旧 IP
    if [ -f "$CURRENT_IP_FILE" ]; then
        OLD_IP=$(cat $CURRENT_IP_FILE)
        report_bad_ip $OLD_IP
    fi

    # 换新 IP
    NEW_IP=$(get_new_ip)
    
    if [ ! -z "$NEW_IP" ]; then
        echo "🎯 替换为新精锐 IP: $NEW_IP"
        
        # 【关键修改位】：这里写你修改配置文件的具体命令
        # 示例：使用 sed 替换配置文件里的旧 IP
        # sed -i "s/$OLD_IP/$NEW_IP/g" $CONFIG_PATH
        
        # 保存新 IP 状态
        echo $NEW_IP > $CURRENT_IP_FILE
        
        # 重启你的代理服务
        # systemctl restart v2ray
        
        echo "✅ 替换完成，等待生效。"
    else
        echo "❌ 弹药库竟然空了，请检查 GitHub Feeder！"
    fi
fi
第三步：设置自动化巡逻
我们通过 crontab 让这个脚本每 5 分钟巡逻一次：

输入 crontab -e

在底部加入这一行：

Bash

*/5 * * * * /bin/bash /root/aegis_monitor.sh >> /root/aegis.log 2>&1
这种设计的“智斗”精髓：
分布式上报：你的 VPS 就是一个“哨兵”。一旦它在实战中挂了，它会立刻向 GitHub 发信号。

禁闭联动：由于你之前的 process_report.py 设置了反馈即禁闭，当你的 VPS 举报后，GitHub 会秒速封锁该 IP。

全局免疫：如果你有 3 台 VPS 都跑这个脚本，只要其中一台发现 IP 挂了，全网（包括你的手机端）拿到的 ips_txt_view.txt 都会同步更新。

下一步行动建议：
完善命令：在脚本的 # 【关键修改位】 处，根据你使用的工具（如 V2Ray, Clash, Xray 等）写好替换 IP 的 sed 命令。

实测：你可以手动断开 VPS 上的代理服务，看脚本是否会自动发 Issue 并去 GitHub 抓新 IP。
