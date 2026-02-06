"""
JARVIS 邮件发送技能
支持 SMTP 发送邮件

Author: gngdingghuan
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Any, Optional, List
from pathlib import Path

from skills.base_skill import BaseSkill, SkillResult, PermissionLevel, create_tool_schema
from config import get_config
from utils.logger import log
from utils.compat import to_thread


class EmailSkill(BaseSkill):
    """邮件发送技能"""
    
    name = "email"
    description = "发送电子邮件，支持 HTML 格式和附件"
    permission_level = PermissionLevel.SAFE_WRITE  # 降低权限级别以便直接发送
    
    def __init__(self):
        super().__init__()
        self.config = get_config()
        # 从环境变量读取 SMTP 配置
        import os
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.sender_email = os.getenv("SENDER_EMAIL", self.smtp_user)
        self.sender_name = os.getenv("SENDER_NAME", "JARVIS")
        # SSL 端口 (465) vs TLS 端口 (587)
        self.use_ssl = self.smtp_port == 465
    
    async def execute(
        self, 
        action: Optional[str] = None,
        to: Optional[str] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        html: bool = False,
        attachments: Optional[List[str]] = None,
        **params
    ) -> SkillResult:
        """执行邮件操作"""
        
        if action == "check_config":
            return self._check_config()
        
        # 默认执行发送
        return await self._send_email(to, subject, body, html, attachments)
    
    def _check_config(self) -> SkillResult:
        """检查 SMTP 配置"""
        if not self.smtp_user or not self.smtp_password:
            return SkillResult(
                success=False,
                output=None,
                error="SMTP 配置缺失，请设置环境变量: SMTP_HOST, SMTP_USER, SMTP_PASSWORD"
            )
        
        return SkillResult(
            success=True,
            output={
                "smtp_host": self.smtp_host,
                "smtp_port": self.smtp_port,
                "smtp_user": self.smtp_user[:3] + "***" + self.smtp_user[-4:] if len(self.smtp_user) > 7 else "***",
                "sender_email": self.sender_email,
                "use_ssl": self.use_ssl
            }
        )
    
    async def _send_email(
        self,
        to: Optional[str],
        subject: Optional[str],
        body: Optional[str],
        html: bool = False,
        attachments: Optional[List[str]] = None
    ) -> SkillResult:
        """发送邮件"""
        
        # 验证参数
        if not to:
            return SkillResult(success=False, output=None, error="缺少收件人: to")
        if not subject:
            return SkillResult(success=False, output=None, error="缺少主题: subject")
        if not body:
            return SkillResult(success=False, output=None, error="缺少内容: body")
        
        # 检查配置
        config_check = self._check_config()
        if not config_check.success:
            return config_check
        
        # 在线程中同步发送
        try:
            result = await to_thread(
                self._send_email_sync, 
                to, subject, body, html, attachments
            )
            return result
        except Exception as e:
            log.error(f"邮件发送失败: {e}")
            return SkillResult(
                success=False,
                output=None,
                error=f"邮件发送失败: {str(e)}"
            )
    
    def _send_email_sync(
        self,
        to: str,
        subject: str,
        body: str,
        html: bool = False,
        attachments: Optional[List[str]] = None
    ) -> SkillResult:
        """同步发送邮件"""
        try:
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            msg['To'] = to
            msg['Subject'] = subject
            
            # 添加正文
            content_type = 'html' if html else 'plain'
            msg.attach(MIMEText(body, content_type, 'utf-8'))
            
            # 添加附件
            if attachments:
                for file_path in attachments:
                    path = Path(file_path)
                    if path.exists():
                        with open(path, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename="{path.name}"'
                            )
                            msg.attach(part)
                    else:
                        log.warning(f"附件文件不存在: {file_path}")
            
            # 发送邮件
            if self.use_ssl:
                # SSL 方式 (端口 465)
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
            else:
                # TLS 方式 (端口 587)
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
            
            log.info(f"邮件发送成功: {to}")
            return SkillResult(
                success=True,
                output={
                    "status": "sent",
                    "to": to,
                    "subject": subject,
                    "message": f"邮件已成功发送至 {to}"
                }
            )
            
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP 认证失败: {e}。如果使用 Gmail，请使用应用专用密码而非账户密码"
            log.error(error_msg)
            return SkillResult(success=False, output=None, error=error_msg)
            
        except smtplib.SMTPConnectError as e:
            error_msg = f"无法连接到 SMTP 服务器 {self.smtp_host}:{self.smtp_port}: {e}"
            log.error(error_msg)
            return SkillResult(success=False, output=None, error=error_msg)
            
        except Exception as e:
            log.error(f"邮件发送失败: {e}")
            return SkillResult(
                success=False,
                output=None,
                error=f"邮件发送失败: {str(e)}"
            )
    
    def get_schema(self) -> Dict[str, Any]:
        return create_tool_schema(
            name=self.name,
            description=self.description,
            parameters={
                "action": {
                    "type": "string",
                    "enum": ["send", "check_config"],
                    "description": "操作类型 (send=发送邮件, check_config=检查配置)",
                    "default": "send"
                },
                "to": {
                    "type": "string",
                    "description": "收件人邮箱地址"
                },
                "subject": {
                    "type": "string",
                    "description": "邮件主题"
                },
                "body": {
                    "type": "string",
                    "description": "邮件正文内容"
                },
                "html": {
                    "type": "boolean",
                    "description": "是否为 HTML 格式",
                    "default": False
                },
                "attachments": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "附件文件路径列表"
                }
            },
            required=["to", "subject", "body"]
        )
