系统使用手册
分发端：你的客户端/代理服务器只需请求 https://raw.githubusercontent.com/用户名/仓库名/main/ips_txt_view.txt 即可获得最优质的 IP。

反馈端：当代理服务器发现某个 IP 连续几次握手失败或速度极慢时，自动调用 GitHub API 创建一个 Issue。

API 调用示例（给你的代理服务器用）：

Bash

curl -X POST -H "Authorization: token <你的TOKEN>" \
     -d '{"title":"FEEDBACK: 1.2.3.4"}' \
     https://api.github.com/repos/用户名/仓库名/issues
结果：GitHub 收到反馈后会自动在 ip_pool.json 里累计次数，达到 5 次后，下次 ips_txt_view.txt 生成时就会彻底消失。24 小时后，aegis_collector.py 运行时会自动将其“刑满释放”。
