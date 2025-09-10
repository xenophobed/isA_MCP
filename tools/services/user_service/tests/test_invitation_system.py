#!/usr/bin/env python3
"""
Test script for the invitation system
Tests email sending and invitation creation
"""

import asyncio
import sys
sys.path.append('.')

from tools.services.user_service.services.email_service import EmailService


async def test_send_invitation_email():
    """Test sending an invitation email"""
    print("🚀 Testing invitation email sending...")
    
    try:
        email_service = EmailService()
        
        # Test invitation data
        invitation_data = {
            'to_email': 'test@example.com',  # Replace with your test email
            'organization_name': 'iaPro.ai Test Organization',
            'inviter_name': 'John Doe',
            'inviter_email': 'john@example.com',
            'role': 'member',
            'invitation_link': 'https://app.iapro.ai/accept-invitation?token=test123',
            'expires_at': '2025-08-14 12:00:00 UTC'
        }
        
        result = await email_service.send_organization_invitation(invitation_data)
        
        if result.is_success:
            print("✅ Invitation email sent successfully!")
            print(f"   Email ID: {result.data.get('id')}")
            print(f"   Status: {result.message}")
            return True
        else:
            print("❌ Failed to send invitation email")
            print(f"   Error: {result.message}")
            if result.error_details:
                print(f"   Details: {result.error_details}")
            return False
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'email_service' in locals():
            await email_service.close()


async def test_welcome_email():
    """Test sending a welcome email"""
    print("\n🚀 Testing welcome email sending...")
    
    try:
        email_service = EmailService()
        
        # Test user data
        user_data = {
            'email': 'test@example.com',  # Replace with your test email
            'name': 'Jane Smith',
            'organization_name': 'iaPro.ai Test Organization'
        }
        
        result = await email_service.send_welcome_email(user_data)
        
        if result.is_success:
            print("✅ Welcome email sent successfully!")
            print(f"   Email ID: {result.data.get('id')}")
            print(f"   Status: {result.message}")
            return True
        else:
            print("❌ Failed to send welcome email")
            print(f"   Error: {result.message}")
            return False
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'email_service' in locals():
            await email_service.close()


async def test_billing_notification():
    """Test sending a billing notification email"""
    print("\n🚀 Testing billing notification email...")
    
    try:
        email_service = EmailService()
        
        # Test billing data
        billing_data = {
            'email': 'test@example.com',  # Replace with your test email
            'type': 'payment_success',
            'amount': 2000,  # $20.00 in cents
            'organization_name': 'iaPro.ai Test Organization',
            'plan_name': 'Pro Plan'
        }
        
        result = await email_service.send_billing_notification(billing_data)
        
        if result.is_success:
            print("✅ Billing notification email sent successfully!")
            print(f"   Email ID: {result.data.get('id')}")
            print(f"   Status: {result.message}")
            return True
        else:
            print("❌ Failed to send billing notification email")
            print(f"   Error: {result.message}")
            return False
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'email_service' in locals():
            await email_service.close()


async def main():
    """Run all email tests"""
    print("📧 Email Service Test Suite")
    print("=" * 50)
    
    tests = [
        ("Invitation Email", test_send_invitation_email),
        ("Welcome Email", test_welcome_email),
        ("Billing Notification", test_billing_notification)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} Test...")
        result = await test_func()
        results.append((test_name, result))
    
    print("\n📊 Test Summary:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Email system is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the logs above for details.")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)