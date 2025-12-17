#!/usr/bin/env python3

import requests
import json

def main():
    base_url = "https://easywasend-1.preview.emergentagent.com"
    
    # Login as admin
    login_response = requests.post(
        f"{base_url}/api/auth/login",
        json={"email": "bizchatapi@gmail.com", "password": "adminpassword"}
    )
    
    if login_response.status_code != 200:
        print("❌ Failed to login")
        return
    
    token = login_response.json()['token']
    headers = {'Authorization': f'Bearer {token}'}
    
    # Get campaigns
    campaigns_response = requests.get(
        f"{base_url}/api/campaigns",
        headers=headers
    )
    
    if campaigns_response.status_code == 200:
        campaigns = campaigns_response.json()['campaigns']
        print(f"📊 Found {len(campaigns)} campaigns")
        
        for campaign in campaigns:
            print(f"\n🔍 Campaign: {campaign['name']}")
            print(f"   ID: {campaign['id']}")
            print(f"   Status: {campaign['status']}")
            print(f"   Recipients: {campaign['totalCount']}")
            if campaign.get('scheduledAt'):
                print(f"   Scheduled for: {campaign['scheduledAt']}")
            print(f"   Created: {campaign['createdAt']}")
    else:
        print(f"❌ Failed to get campaigns: {campaigns_response.status_code}")

if __name__ == "__main__":
    main()