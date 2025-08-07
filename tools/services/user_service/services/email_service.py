"""
Email Service - Resend Integration

邮件服务实现，使用Resend API
支持组织成员邀请邮件，事务性邮件等
"""

import json
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from .base import BaseService, ServiceResult
from ..config import get_config

logger = logging.getLogger(__name__)


class EmailService(BaseService):
    """邮件服务 - 使用Resend API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化邮件服务
        
        Args:
            api_key: Resend API密钥，如果不提供则从环境变量读取
        """
        super().__init__("EmailService")
        self.config = get_config()
        
        # 使用提供的API密钥或配置中的密钥
        self.api_key = api_key or "re_PFqcCYGx_7QGBTd81pyJeYNMCbkGLZV8w"
        self.base_url = "https://api.resend.com"
        
        # 默认发件人
        self.default_from = "noreply@iapro.ai"
        
        # HTTP客户端
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
    
    async def send_email(self, to: str | List[str], subject: str, html_content: str,
                        text_content: Optional[str] = None, from_email: Optional[str] = None,
                        reply_to: Optional[str] = None) -> ServiceResult[Dict[str, Any]]:
        """
        发送邮件
        
        Args:
            to: 收件人邮箱地址
            subject: 邮件主题
            html_content: HTML邮件内容
            text_content: 纯文本邮件内容（可选）
            from_email: 发件人邮箱（可选）
            reply_to: 回复邮箱（可选）
            
        Returns:
            ServiceResult[Dict]: 发送结果
        """
        try:
            self._log_operation("send_email", f"to={to}, subject={subject}")
            
            # 准备邮件数据
            email_data = {
                "from": from_email or self.default_from,
                "to": to if isinstance(to, list) else [to],
                "subject": subject,
                "html": html_content
            }
            
            if text_content:
                email_data["text"] = text_content
            
            if reply_to:
                email_data["reply_to"] = reply_to
            
            # 发送邮件
            response = await self.client.post("/emails", json=email_data)
            
            if response.status_code == 200:
                result_data = response.json()
                self._log_operation("email_sent", f"email_id={result_data.get('id')}")
                
                return ServiceResult.success(
                    data=result_data,
                    message="Email sent successfully"
                )
            else:
                error_data = response.json() if response.content else {"error": "Unknown error"}
                return ServiceResult.error(
                    message=f"Failed to send email: {error_data.get('message', 'Unknown error')}",
                    error_details=error_data
                )
                
        except Exception as e:
            return self._handle_exception(e, "send email")
    
    async def send_organization_invitation(self, invitation_data: Dict[str, Any]) -> ServiceResult[Dict[str, Any]]:
        """
        发送组织邀请邮件
        
        Args:
            invitation_data: 邀请数据
                - to_email: 被邀请人邮箱
                - organization_name: 组织名称
                - inviter_name: 邀请人姓名
                - inviter_email: 邀请人邮箱
                - role: 角色
                - invitation_link: 邀请链接
                - expires_at: 过期时间
                
        Returns:
            ServiceResult[Dict]: 发送结果
        """
        try:
            self._log_operation("send_organization_invitation", f"to={invitation_data.get('to_email')}")
            
            # 邮件主题
            subject = f"Invitation to join {invitation_data['organization_name']}"
            
            # HTML邮件内容
            html_content = self._build_invitation_html(invitation_data)
            
            # 纯文本内容
            text_content = self._build_invitation_text(invitation_data)
            
            # 发送邮件
            result = await self.send_email(
                to=invitation_data['to_email'],
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                reply_to=invitation_data.get('inviter_email')
            )
            
            if result.is_success:
                self._log_operation("invitation_email_sent", f"to={invitation_data.get('to_email')}")
            
            return result
            
        except Exception as e:
            return self._handle_exception(e, "send organization invitation")
    
    async def send_welcome_email(self, user_data: Dict[str, Any]) -> ServiceResult[Dict[str, Any]]:
        """
        发送欢迎邮件
        
        Args:
            user_data: 用户数据
                - email: 用户邮箱
                - name: 用户姓名
                - organization_name: 组织名称（可选）
                
        Returns:
            ServiceResult[Dict]: 发送结果
        """
        try:
            self._log_operation("send_welcome_email", f"to={user_data.get('email')}")
            
            subject = "Welcome to iaPro.ai!"
            
            html_content = self._build_welcome_html(user_data)
            text_content = self._build_welcome_text(user_data)
            
            return await self.send_email(
                to=user_data['email'],
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
        except Exception as e:
            return self._handle_exception(e, "send welcome email")
    
    async def send_billing_notification(self, billing_data: Dict[str, Any]) -> ServiceResult[Dict[str, Any]]:
        """
        发送账单通知邮件
        
        Args:
            billing_data: 账单数据
                - email: 用户邮箱
                - type: 通知类型 (payment_success, payment_failed, subscription_renewed, etc.)
                - amount: 金额
                - organization_name: 组织名称
                - plan_name: 计划名称
                
        Returns:
            ServiceResult[Dict]: 发送结果
        """
        try:
            notification_type = billing_data['type']
            self._log_operation("send_billing_notification", f"type={notification_type}, to={billing_data.get('email')}")
            
            subject_map = {
                'payment_success': 'Payment Successful',
                'payment_failed': 'Payment Failed',
                'subscription_renewed': 'Subscription Renewed',
                'subscription_cancelled': 'Subscription Cancelled',
                'credit_low': 'Credit Balance Low Warning'
            }
            
            subject = subject_map.get(notification_type, 'Billing Notification')
            
            html_content = self._build_billing_html(billing_data)
            text_content = self._build_billing_text(billing_data)
            
            return await self.send_email(
                to=billing_data['email'],
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
        except Exception as e:
            return self._handle_exception(e, "send billing notification")
    
    def _build_invitation_html(self, data: Dict[str, Any]) -> str:
        """构建邀请邮件HTML内容"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Organization Invitation</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2563eb; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 8px 8px; }}
                .button {{ display: inline-block; background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #6b7280; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>You're Invited!</h1>
                </div>
                <div class="content">
                    <p>Hi there!</p>
                    <p><strong>{data.get('inviter_name', 'Someone')}</strong> has invited you to join <strong>{data['organization_name']}</strong> on iaPro.ai.</p>
                    <p>You've been invited with the role: <strong>{data.get('role', 'member')}</strong></p>
                    <p>Click the button below to accept the invitation:</p>
                    <a href="{data['invitation_link']}" class="button">Accept Invitation</a>
                    <p>This invitation will expire on {data.get('expires_at', 'N/A')}.</p>
                    <p>If you have any questions, you can reply to this email to contact {data.get('inviter_name', 'the inviter')}.</p>
                    <p>Best regards,<br>The iaPro.ai Team</p>
                </div>
                <div class="footer">
                    <p>If you're having trouble clicking the button, copy and paste this URL into your browser:<br>
                    {data['invitation_link']}</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _build_invitation_text(self, data: Dict[str, Any]) -> str:
        """构建邀请邮件纯文本内容"""
        return f"""
You're Invited to {data['organization_name']}!

Hi there!

{data.get('inviter_name', 'Someone')} has invited you to join {data['organization_name']} on iaPro.ai.

You've been invited with the role: {data.get('role', 'member')}

To accept the invitation, please visit:
{data['invitation_link']}

This invitation will expire on {data.get('expires_at', 'N/A')}.

If you have any questions, you can reply to this email to contact {data.get('inviter_name', 'the inviter')}.

Best regards,
The iaPro.ai Team
        """
    
    def _build_welcome_html(self, data: Dict[str, Any]) -> str:
        """构建欢迎邮件HTML内容"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Welcome to iaPro.ai</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2563eb; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 8px 8px; }}
                .button {{ display: inline-block; background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to iaPro.ai!</h1>
                </div>
                <div class="content">
                    <p>Hi {data.get('name', 'there')}!</p>
                    <p>Welcome to iaPro.ai! We're excited to have you on board.</p>
                    {f"<p>You've been added to the organization: <strong>{data['organization_name']}</strong></p>" if data.get('organization_name') else ""}
                    <p>Here's what you can do next:</p>
                    <ul>
                        <li>Explore your dashboard</li>
                        <li>Set up your organization</li>
                        <li>Invite team members</li>
                        <li>Start using our AI services</li>
                    </ul>
                    <p>If you have any questions, don't hesitate to reach out to our support team.</p>
                    <p>Best regards,<br>The iaPro.ai Team</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _build_welcome_text(self, data: Dict[str, Any]) -> str:
        """构建欢迎邮件纯文本内容"""
        org_text = f"\n\nYou've been added to the organization: {data['organization_name']}" if data.get('organization_name') else ""
        
        return f"""
Welcome to iaPro.ai!

Hi {data.get('name', 'there')}!

Welcome to iaPro.ai! We're excited to have you on board.{org_text}

Here's what you can do next:
- Explore your dashboard
- Set up your organization  
- Invite team members
- Start using our AI services

If you have any questions, don't hesitate to reach out to our support team.

Best regards,
The iaPro.ai Team
        """
    
    def _build_billing_html(self, data: Dict[str, Any]) -> str:
        """构建账单通知邮件HTML内容"""
        notification_type = data['type']
        
        content_map = {
            'payment_success': f"Your payment of ${data.get('amount', 0)/100:.2f} was successful!",
            'payment_failed': f"Your payment of ${data.get('amount', 0)/100:.2f} failed. Please update your payment method.",
            'subscription_renewed': f"Your {data.get('plan_name', 'subscription')} has been renewed successfully.",
            'subscription_cancelled': f"Your {data.get('plan_name', 'subscription')} has been cancelled.",
            'credit_low': f"Your credit balance is running low. Consider upgrading your plan."
        }
        
        content = content_map.get(notification_type, "Billing notification")
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Billing Notification</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2563eb; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 8px 8px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Billing Notification</h1>
                </div>
                <div class="content">
                    <p>Hi there!</p>
                    <p>{content}</p>
                    {f"<p>Organization: <strong>{data['organization_name']}</strong></p>" if data.get('organization_name') else ""}
                    <p>If you have any questions about your billing, please contact our support team.</p>
                    <p>Best regards,<br>The iaPro.ai Team</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _build_billing_text(self, data: Dict[str, Any]) -> str:
        """构建账单通知邮件纯文本内容"""
        notification_type = data['type']
        
        content_map = {
            'payment_success': f"Your payment of ${data.get('amount', 0)/100:.2f} was successful!",
            'payment_failed': f"Your payment of ${data.get('amount', 0)/100:.2f} failed. Please update your payment method.",
            'subscription_renewed': f"Your {data.get('plan_name', 'subscription')} has been renewed successfully.",
            'subscription_cancelled': f"Your {data.get('plan_name', 'subscription')} has been cancelled.",
            'credit_low': f"Your credit balance is running low. Consider upgrading your plan."
        }
        
        content = content_map.get(notification_type, "Billing notification")
        org_text = f"\nOrganization: {data['organization_name']}" if data.get('organization_name') else ""
        
        return f"""
Billing Notification

Hi there!

{content}{org_text}

If you have any questions about your billing, please contact our support team.

Best regards,
The iaPro.ai Team
        """
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# 便捷函数
async def send_organization_invitation_email(invitation_data: Dict[str, Any]) -> ServiceResult[Dict[str, Any]]:
    """
    发送组织邀请邮件的便捷函数
    
    Args:
        invitation_data: 邀请数据
        
    Returns:
        ServiceResult[Dict]: 发送结果
    """
    async with EmailService() as email_service:
        return await email_service.send_organization_invitation(invitation_data)


async def send_welcome_email(user_data: Dict[str, Any]) -> ServiceResult[Dict[str, Any]]:
    """
    发送欢迎邮件的便捷函数
    
    Args:
        user_data: 用户数据
        
    Returns:
        ServiceResult[Dict]: 发送结果
    """
    async with EmailService() as email_service:
        return await email_service.send_welcome_email(user_data)


async def send_billing_notification_email(billing_data: Dict[str, Any]) -> ServiceResult[Dict[str, Any]]:
    """
    发送账单通知邮件的便捷函数
    
    Args:
        billing_data: 账单数据
        
    Returns:
        ServiceResult[Dict]: 发送结果
    """
    async with EmailService() as email_service:
        return await email_service.send_billing_notification(billing_data)