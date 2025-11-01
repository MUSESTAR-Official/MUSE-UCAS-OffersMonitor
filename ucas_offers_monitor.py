import requests
import json
import time
import os
import sys
import signal
import re
from datetime import datetime
from urllib.parse import quote
import base64
import uuid

def get_version():
    try:
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        version_file = os.path.join(base_path, "version_info.txt")
        
        if os.path.exists(version_file):
            with open(version_file, 'r', encoding='utf-8') as f:
                content = f.read()
                match = re.search(r"StringStruct\(u'ProductVersion',\s*u'([^']+)'\)", content)
                if match:
                    return match.group(1)
        
        return "0.0.0"
    except Exception as e:
        return "0.0.0"

def show_muse_banner():
    banner = r"""
          _____                    _____                    _____                    _____          
         /\    \                  /\    \                  /\    \                  /\    \         
        /::\____\                /::\____\                /::\    \                /::\    \        
       /::::|   |               /:::/    /               /::::\    \              /::::\    \       
      /:::::|   |              /:::/    /               /::::::\    \            /::::::\    \      
     /::::::|   |             /:::/    /               /:::/\:::\    \          /:::/\:::\    \     
    /:::/|::|   |            /:::/    /               /:::/__\:::\    \        /:::/__\:::\    \    
   /:::/ |::|   |           /:::/    /                \:::\   \:::\    \      /::::\   \:::\    \   
  /:::/  |::|___|______    /:::/    /      _____    ___\:::\   \:::\    \    /::::::\   \:::\    \  
 /:::/   |::::::::\    \  /:::/____/      /\    \  /\   \:::\   \:::\    \  /:::/\:::\   \:::\    \ 
/:::/    |:::::::::\____\|:::|    /      /::\____\/::\   \:::\   \:::\____\/:::/__\:::\   \:::\____\
\::/    / ~~~~~/:::/    /|:::|____\     /:::/    /\:::\   \:::\   \::/    /\:::\   \:::\   \::/    /
 \/____/      /:::/    /  \:::\    \   /:::/    /  \:::\   \:::\   \/____/  \:::\   \:::\   \/____/ 
             /:::/    /    \:::\    \ /:::/    /    \:::\   \:::\    \       \:::\   \:::\    \     
            /:::/    /      \:::\    /:::/    /      \:::\   \:::\____\       \:::\   \:::\____\    
           /:::/    /        \:::\__/:::/    /        \:::\  /:::/    /        \:::\   \::/    /    
          /:::/    /          \::::::::/    /          \:::\/:::/    /          \:::\   \/____/     
         /:::/    /            \::::::/    /            \::::::/    /            \:::\    \         
        /:::/    /              \::::/    /              \::::/    /              \:::\____\        
        \::/    /                \::/____/                \::/    /                \::/    /        
         \/____/                  ~~                       \/____/                  \/____/                                                                                                        
    """
    print(banner)
    version = get_version()
    print(f"MUSE-UCAS-OffersMonitor v{version}")
    print("=" * 88)
    print()

class UCASOffersMonitor:
    def __init__(self):
        self.config_file = 'ucas-offersmonitor-cookies.json'
        self.config = self.load_config()
        self.last_offers_count = None
        self.login_retry_count = 0
        self.max_login_retries = 2
        
    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {}
        except Exception as e:
            print(f"配置文件加载失败: {e}")
            return {}
    
    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"配置文件保存失败: {e}")
    
    def setup_config(self):
        print("\n请选择登录方式:")
        print("1. 直接输入cookies")
        print("2. 使用账号密码登录")
        
        while True:
            choice = input("请选择 (1/2): ").strip()
            if choice == '1':
                cookies = input("请输入完整的cookies: ").strip()
                if cookies:
                    self.config['cookies'] = cookies
                    break
                else:
                    print("❌ cookies不能为空")
            elif choice == '2':
                username = input("请输入UCAS用户名: ").strip()
                password = input("请输入UCAS密码: ").strip()
                if username and password:
                    self.config['username'] = username
                    self.config['password'] = password
                    if self.login_with_credentials():
                        break
                    else:
                        print("❌ 登录失败，请检查账号密码")
                        return False
                else:
                    print("❌ 用户名和密码不能为空")
            else:
                print("❌ 请输入 1 或 2")
        
        bark_key = input("请输入Bark推送key (直接回车可跳过): ").strip()
        if bark_key:
            self.config['bark_key'] = bark_key
            print("Bark推送已配置")
        else:
            print("已跳过Bark推送配置")
        self.save_config()
        print("配置保存成功")
        return True
    
    def get_bootstrap_cookies(self):
        try:
            session = requests.Session()
            bootstrap_url = "https://7054541.ucas.com/accounts.webSdkBootstrap"
            
            bootstrap_data = {
                'apiKey': '3_-T_rRw2AdTdZQrVXfo9l-h8Uqzn3hGrZCHHfvRg-ITrJ0cZMfHuAmo9YpLYQbTjo',
                'pageURL': 'https://accounts.ucas.com/account/login',
                'sdk': 'js_latest',
                'sdkBuild': '18051',
                'format': 'json'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': 'https://accounts.ucas.com/account/login'
            }
            
            response = session.post(bootstrap_url, data=bootstrap_data, headers=headers)
            
            if response.status_code == 200:
                print("Bootstrap cookies获取成功")
                return session
            else:
                print(f"❌ Bootstrap cookies获取失败: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 获取bootstrap cookies失败: {e}")
            return None

    def extract_login_token_from_cookies(self, session):
        try:
            for cookie in session.cookies:
                if cookie.name.startswith('glt_'):
                    print(f"成功提取login token")
                    return cookie.value
            print("❌ 未找到login token")
            return None
        except Exception as e:
            print(f"❌ 提取login token失败: {e}")
            return None

    def get_jwt_token(self, session, login_token):
        try:
            jwt_url = "https://7054541.ucas.com/accounts.getJWT"
            
            jwt_data = {
                'fields': 'firstName, lastName, email, data.bypassVarnishCache, data.hasFinalised, locale, photoURL, thumbnailURL, data.lastLoginDevice, lastLoginTimestamp, data.userTypes, data.userTypePreference, rbaPolicy.riskPolicy',
                'APIKey': '3_-T_rRw2AdTdZQrVXfo9l-h8Uqzn3hGrZCHHfvRg-ITrJ0cZMfHuAmo9YpLYQbTjo',
                'sdk': 'js_latest',
                'login_token': login_token,
                'authMode': 'cookie',
                'pageURL': 'https://accounts.ucas.com/account/login',
                'sdkBuild': '18051',
                'format': 'json'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': 'https://accounts.ucas.com/account/login'
            }
            
            response = session.post(jwt_url, data=jwt_data, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('errorCode') == 0:
                    jwt_token = result.get('id_token')
                    if jwt_token:
                        print(f"JWT token获取成功")
                        return jwt_token
                    else:
                        print("❌ JWT响应中未找到id_token")
                        return None
                else:
                    print(f"❌ 获取JWT失败: {result.get('errorMessage', '未知错误')}")
                    return None
            else:
                print(f"❌ JWT请求失败: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 获取JWT token失败: {e}")
            return None

    def parse_jwt_token(self, jwt_token):
        try:
            parts = jwt_token.split('.')
            if len(parts) != 3:
                return None
            
            payload = parts[1]
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding
            
            decoded_payload = base64.urlsafe_b64decode(payload)
            return json.loads(decoded_payload)
            
        except Exception as e:
            print(f"解析JWT token失败: {e}")
            return None

    def generate_device_id(self):
        return str(uuid.uuid4()).replace('-', '')

    def login_callback(self, session, jwt_token):
        try:
            user_info = self.parse_jwt_token(jwt_token)
            if not user_info:
                print("❌ 无法解析JWT token")
                return False
            
            callback_url = "https://accounts.ucas.com/account/logincallback"
            
            email = user_info.get('email', '')
            user_types = user_info.get('data.userTypes', 'Student')
            user_type_preference = user_info.get('data.userTypePreference', 'Student')
            ucas_account_id = user_info.get('sub', '')
            
            callback_data = {
                "token": jwt_token,
                "level": 10,
                "presentLoginDevice": self.generate_device_id(),
                "isSSO": False,
                "User": {
                    "Email": email,
                    "UserTypes": user_types,
                    "UserTypePreference": user_type_preference,
                    "UcasAccountId": ucas_account_id
                }
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
                'Content-Type': 'application/json',
                'Referer': 'https://accounts.ucas.com/account/login',
                'X-NewRelic-ID': 'eyJ2IjpbMCwxXSwiZCI6eyJ0eSI6IkJyb3dzZXIiLCJhYyI6Ijk4Nzg4NiIsImFwIjoiMTEyMDM0MzUzMyIsImlkIjoiMWU4ZmExZTliYWM5YTcyNCIsInRyIjoiYjg5ZGEwYmMwYWMzNDgwNmVmZmVjODdmNzRkYzRmZTQiLCJ0aSI6MTc2MTg5OTUxMTkzMiwidGsiOiIxMzc5MDc3In19'
            }
            
            response = session.post(callback_url, json=callback_data, headers=headers)
            
            if response.status_code == 200:
                for cookie in session.cookies:
                    if cookie.name == 'UcasIdentity':
                        print("成功获取UcasIdentity cookie")
                        return True
                print("❌ 未获取到UcasIdentity cookie")
                return False
            else:
                print(f"❌ Login callback失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Login callback失败: {e}")
            return False

    def login_with_credentials(self):
        try:
            session = self.get_bootstrap_cookies()
            if not session:
                print("❌ 无法获取必要的cookies")
                return False
            
            login_url = "https://7054541.ucas.com/accounts.login"
            
            login_data = {
                'loginID': self.config['username'],
                'password': self.config['password'],
                'sessionExpiration': '0',
                'targetEnv': 'jssdk',
                'include': 'profile,data,emails,subscriptions,preferences,',
                'includeUserInfo': 'true',
                'loginMode': 'standard',
                'lang': 'en',
                'riskContext': '{"b0":449227,"b1":[860,1684,1272,1838],"b2":10,"b3":[],"b4":5,"b5":2,"b6":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0","b7":[{"name":"PDF Viewer","filename":"internal-pdf-viewer","length":2},{"name":"Chrome PDF Viewer","filename":"internal-pdf-viewer","length":2},{"name":"Chromium PDF Viewer","filename":"internal-pdf-viewer","length":2},{"name":"Microsoft Edge PDF Viewer","filename":"internal-pdf-viewer","length":2},{"name":"WebKit built-in PDF","filename":"internal-pdf-viewer","length":2}],"b8":"15:33:08","b9":-480,"b10":{"state":"prompt"},"b11":false,"b12":{"charging":null,"chargingTime":null,"dischargingTime":null,"level":null},"b13":[null,"2560|1440|24",false,true]}',
                'APIKey': '3_-T_rRw2AdTdZQrVXfo9l-h8Uqzn3hGrZCHHfvRg-ITrJ0cZMfHuAmo9YpLYQbTjo',
                'source': 'showScreenSet',
                'sdk': 'js_latest',
                'authMode': 'cookie',
                'pageURL': 'https://accounts.ucas.com/account/login',
                'sdkBuild': '18051',
                'format': 'json'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': 'https://accounts.ucas.com/account/login'
            }
            
            response = session.post(login_url, data=login_data, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('errorCode') == 0:
                    login_token = self.extract_login_token_from_cookies(session)
                    if not login_token:
                        return False
                    
                    jwt_token = self.get_jwt_token(session, login_token)
                    if not jwt_token:
                        return False
                    
                    if self.login_callback(session, jwt_token):
                        all_cookies = []
                        for cookie in session.cookies:
                            all_cookies.append(f"{cookie.name}={cookie.value}")
                        
                        if all_cookies:
                            self.config['cookies'] = '; '.join(all_cookies)
                            print(f"成功保存登录信息")
                            return True
                        else:
                            print("❌ 登录成功但未获取到cookies")
                            return False
                    else:
                        return False
                else:
                    print(f"❌ 账号密码登录失败: {result.get('errorMessage', '未知错误')}")
                    return False
            else:
                print(f"❌ 登录请求失败: {response.status_code}")
                return False
            
        except Exception as e:
            print(f"❌ 登录失败: {e}")
            return False
    
    def get_offers_count(self):
        try:
            url = "https://services.ucas.com/track/service/ugtrackapi/application/applicationstatusmessage"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
                'Cookie': self.config.get('cookies', ''),
                'Referer': 'https://services.ucas.com/',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin'
            }
            
            session = requests.Session()
            session.headers.update(headers)
            
            response = session.get(url, timeout=30)
            
            if response.status_code == 200:
                if not response.text.strip():
                    print(f"❌ 服务器返回空响应")
                    return None
                
                if response.encoding is None or response.encoding == 'ISO-8859-1':
                    response.encoding = 'utf-8'
                
                content_type = response.headers.get('content-type', '').lower()
                if 'application/json' not in content_type and 'text/plain' not in content_type:
                    print(f"❌ 服务器返回非JSON格式响应，Content-Type: {content_type}")
                    print(f"响应内容前200字符: {response.text[:200]}")
                    return None
                
                try:
                    data = response.json()
                    # 优先使用numberOfOffersMade字段，如果不存在则使用totalOffers作为备选
                    offers_count = data.get('numberOfOffersMade', data.get('totalOffers', 0))
                    print(f"解析到的offers数量: {offers_count}")
                    return offers_count
                except json.JSONDecodeError as json_err:
                    print(f"❌ JSON解析失败: {json_err}")
                    print(f"响应状态码: {response.status_code}")
                    print(f"响应编码: {response.encoding}")
                    print(f"原始响应长度: {len(response.content)} bytes")
                    print(f"文本响应长度: {len(response.text)} chars")
                    print(f"响应内容前200字符: {repr(response.text[:200])}")
                    try:
                        for encoding in ['utf-8', 'utf-8-sig', 'gbk', 'gb2312']:
                            try:
                                decoded_text = response.content.decode(encoding)
                                test_data = json.loads(decoded_text)
                                print(f"✅ 使用 {encoding} 编码成功解析")
                                # 优先使用numberOfOffersMade字段，如果不存在则使用totalOffers作为备选
                                offers_count = test_data.get('numberOfOffersMade', test_data.get('totalOffers', 0))
                                print(f"解析到的offers数量: {offers_count}")
                                return offers_count
                            except (UnicodeDecodeError, json.JSONDecodeError):
                                continue
                    except Exception as fallback_err:
                        print(f"❌ 编码修复尝试失败: {fallback_err}")
                    
                    return None
                    
            elif response.status_code == 401:
                return 'AUTH_FAILED'
            else:
                print(f"❌ 请求失败，状态码: {response.status_code}")
                print(f"响应内容: {response.text[:200]}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"❌ 请求超时")
            return None
        except requests.exceptions.RequestException as req_err:
            print(f"❌ 网络请求失败: {req_err}")
            return None
        except Exception as e:
            print(f"❌ 获取offers信息失败: {e}")
            return None
    
    def send_bark_notification(self, title, message):
        try:
            bark_key = self.config.get('bark_key')
            if not bark_key:
                return True
            
            encoded_message = quote(message)
            encoded_title = quote(title)
            
            url = f"https://api.day.app/{bark_key}/{encoded_message}?title={encoded_title}&level=critical&volume=10&call=1&icon=https://data.musestar.cc/files/ms.png"
            
            response = requests.get(url)
            if response.status_code == 200:
                print(f"推送通知已发送")
                return True
            else:
                print(f"推送失败，仅控制台显示")
                return False
                
        except Exception as e:
            print(f"推送通知失败: {e}")
            return False
    
    def handle_auth_failure(self):
        if not self.config.get('username') or not self.config.get('password'):
            message = "Cookies已失效，但未保存账号密码，无法自动重新登录"
            print(f"❌ UCAS登录失效: {message}")
            self.send_bark_notification("❌ UCAS登录失效", message)
            return False
        
        if self.login_retry_count >= self.max_login_retries:
            message = f"已尝试{self.max_login_retries}次重新登录均失败，请检查问题"
            print(f"❌ UCAS登录失败: {message}")
            self.send_bark_notification("❌ UCAS登录失败", message)
            return False
        
        self.login_retry_count += 1
        print(f"Cookies失效，尝试第{self.login_retry_count}次重新登录")
        
        if self.login_with_credentials():
            self.save_config()
            print("重新登录成功，继续监控")
            self.login_retry_count = 0
            return True
        else:
            print(f"❌ 第{self.login_retry_count}次重新登录失败")
            return False

    def monitor_offers(self):
        
        while True:
            try:
                current_offers = self.get_offers_count()
                
                if current_offers == 'AUTH_FAILED':
                    if not self.handle_auth_failure():
                        break
                    continue
                
                if current_offers is not None:
                    if self.last_offers_count is None:
                        self.last_offers_count = current_offers
                        print(f"初始化监控，当前offers数量: {current_offers}")
                    elif current_offers != self.last_offers_count:
                        change = current_offers - self.last_offers_count
                        if change > 0:
                            title = "🎉您收到了一封新的Offer"
                            message = f"请前往UCAS官网查看！新增{change}个offer，当前总数: {current_offers}"
                        else:
                            title = "Offers状态更新"
                            message = f"您的offers数量从 {self.last_offers_count} 变更为 {current_offers}"
                        
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")
                        self.send_bark_notification(title, message)
                        self.last_offers_count = current_offers
                    else:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 当前offers数量: {current_offers} (无变化)")
                else:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 获取offers信息失败，60秒后重试")
                
                time.sleep(60)
                
            except KeyboardInterrupt:
                print("\n监控已停止")
                break
            except Exception as e:
                print(f"监控过程中发生错误: {e}")
                time.sleep(60)
    
    def run(self):
        show_muse_banner()
        
        if self.config.get('cookies'):
            print("检测到已有配置")
            use_existing = input("是否使用现有配置？(y/n): ").lower()
            if use_existing != 'y':
                if not self.setup_config():
                    return False
        else:
            print("未检测到配置文件")
            if not self.setup_config():
                return False
        
        print("正在测试配置")
        offers_count = self.get_offers_count()
        
        if offers_count == 'AUTH_FAILED':
            if not self.handle_auth_failure():
                return False
            offers_count = self.get_offers_count()
        
        if offers_count is not None and offers_count != 'AUTH_FAILED':
            print(f"配置测试成功，当前offers数量: {offers_count}")
            
            if self.config.get('bark_key'):
                test_notification = input("是否发送测试通知？(y/n): ").lower()
                if test_notification == 'y':
                    self.send_bark_notification("🔔UCAS监控测试", "监控脚本配置成功，开始监控offers变化")
            else:
                print("未配置Bark密钥，跳过推送通知")
        else:
            print("❌ 配置测试失败")
            return False
        
        print("\n开始监控UCAS Offers变化")
        self.monitor_offers()
        return True

def main():
    while True:
        try:
            monitor = UCASOffersMonitor()
            success = monitor.run()
            if not success:
                print("\n程序配置或运行失败")
        except KeyboardInterrupt:
            print("\n\n程序已被用户中断")
        except Exception as e:
            import traceback
            print(f"\n❌ 程序运行出错: {e}")
            print("\n完整错误详情:")
            print(traceback.format_exc())
        
        print("\n" + "=" * 60)
        while True:
            choice = input("退出程序(T) / 重新开始(S): ").strip().upper()
            if choice == 'T':
                print("\n程序已退出")
                return
            elif choice == 'S':
                print("\n重新启动程序\n")
                break
            else:
                print("❌ 请输入 T (退出) 或 S (重新开始)")

if __name__ == "__main__":
    main()
