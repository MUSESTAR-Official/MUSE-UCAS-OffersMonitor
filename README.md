# UCAS申请状态监控工具

这是一个用于监控UCAS申请状态和Offers变化的Python脚本，当检测到Offers数量变化时会通过Bark推送通知。

## 功能特性

- 支持直接输入cookies或账号密码登录
- 自动保存登录信息和配置到本地文件
- 每3分钟自动检查Offers状态变化
- 通过Bark推送实时通知到手机

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

1. 运行脚本：
   ```bash
   python ucas_offers_monitor.py
   ```
   （或直接下载Releases中打包好的exe文件）

2. 输入您的UCAS cookies或账号密码

3. 输入Bark推送密钥

4. 开始监控

## 注意事项

- 建议先在测试环境中验证脚本功能
- 请遵守UCAS网站的使用条款和相关法律法规

## 免责声明

本脚本仅供学习和个人使用，使用者需自行承担使用风险。作者不对因使用本脚本造成的任何损失负责。