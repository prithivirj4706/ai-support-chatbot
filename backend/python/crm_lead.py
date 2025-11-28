"""Zoho CRM API Integration for Lead Creation and Management.

Handles:
- Creating new leads in Zoho CRM
- Updating existing leads
- Creating tasks/follow-ups
- Retrieving lead data
- Error handling with retries
"""

import httpx
import logging
import asyncio
import os
from typing import Dict, Optional, List
from datetime import datetime
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class ZohoCRMClient:
    """Client for Zoho CRM API v2."""

    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        refresh_token: str = None,
        crm_url: str = None,
    ):
        self.client_id = client_id or os.getenv('ZOHO_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('ZOHO_CLIENT_SECRET')
        self.refresh_token = refresh_token or os.getenv('ZOHO_REFRESH_TOKEN')
        self.crm_url = crm_url or os.getenv('ZOHO_CRM_URL', 'https://www.zohoapis.in')
        self.access_token = None
        self.token_expiry = None

    async def get_access_token(self) -> str:
        """Get or refresh the access token."""
        if self.access_token and self.token_expiry > datetime.now():
            return self.access_token

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{self.crm_url}/oauth/v2/token',
                data={
                    'refresh_token': self.refresh_token,
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'grant_type': 'refresh_token',
                },
            )

            if response.status_code != 200:
                raise Exception(f'Failed to refresh token: {response.text}')

            data = response.json()
            self.access_token = data['access_token']
            # Token expires in 3600 seconds, set expiry to 55 minutes
            self.token_expiry = datetime.now().replace(second=0, microsecond=0)
            return self.access_token

    async def create_lead(self, lead_data: Dict) -> Dict:
        """Create a new lead in Zoho CRM.
        
        Args:
            lead_data: Dict with lead fields
            {
                'first_name': str,
                'last_name': str,
                'email': str,
                'phone': str,
                'company': str,
                'lead_source': str,
                'description': str,
                'custom_field_1': str,  # e.g. lead_score
                'custom_field_2': str,  # e.g. business_type
            }
        
        Returns:
            Dict with lead ID and response data
        """
        token = await self.get_access_token()

        # Map lead data to Zoho CRM fields
        crm_payload = {
            'data': [
                {
                    'First_Name': lead_data.get('first_name', ''),
                    'Last_Name': lead_data.get('last_name', ''),
                    'Email': lead_data.get('email', ''),
                    'Phone': lead_data.get('phone', ''),
                    'Company': lead_data.get('company', ''),
                    'Lead_Source': lead_data.get('lead_source', 'Website Chat'),
                    'Description': lead_data.get('description', ''),
                    'Lead_Score__c': lead_data.get('lead_score', 50),
                    'Business_Type__c': lead_data.get('business_type', ''),
                }
            ]
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{self.crm_url}/crm/v2/Leads',
                headers={'Authorization': f'Bearer {token}'},
                json=crm_payload,
            )

            if response.status_code not in [200, 201]:
                logger.error(f'CRM Lead creation failed: {response.text}')
                raise Exception(f'Lead creation failed: {response.status_code}')

            data = response.json()
            lead_id = data['data'][0]['id']
            logger.info(f'Lead created: {lead_id}')
            return {'lead_id': lead_id, 'data': data}

    async def create_task(self, lead_id: str, task_data: Dict) -> Dict:
        """Create a follow-up task for a lead.
        
        Args:
            lead_id: Zoho Lead ID
            task_data: Task details
            {
                'subject': str,
                'description': str,
                'due_date': str (YYYY-MM-DD),
                'priority': 'High' | 'Medium' | 'Low',
                'owner': str (Zoho user ID),
            }
        
        Returns:
            Task ID and response data
        """
        token = await self.get_access_token()

        task_payload = {
            'data': [
                {
                    'Subject': task_data.get('subject', ''),
                    'Description': task_data.get('description', ''),
                    'Due_Date': task_data.get('due_date'),
                    'Priority': task_data.get('priority', 'Medium'),
                    'Who_Id': lead_id,
                }
            ]
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{self.crm_url}/crm/v2/Tasks',
                headers={'Authorization': f'Bearer {token}'},
                json=task_payload,
            )

            if response.status_code not in [200, 201]:
                logger.error(f'Task creation failed: {response.text}')
                raise Exception(f'Task creation failed: {response.status_code}')

            data = response.json()
            task_id = data['data'][0]['id']
            logger.info(f'Task created: {task_id} for lead {lead_id}')
            return {'task_id': task_id, 'data': data}

    async def get_lead(self, lead_id: str) -> Dict:
        """Fetch a lead by ID."""
        token = await self.get_access_token()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{self.crm_url}/crm/v2/Leads/{lead_id}',
                headers={'Authorization': f'Bearer {token}'},
            )

            if response.status_code != 200:
                raise Exception(f'Lead fetch failed: {response.status_code}')

            return response.json()

    async def search_leads_by_email(self, email: str) -> List[Dict]:
        """Search for leads by email address."""
        token = await self.get_access_token()

        # Use Zoho CRM search criteria
        criteria = f'(Email:equals:{email})'

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{self.crm_url}/crm/v2/Leads/search',
                headers={'Authorization': f'Bearer {token}'},
                params={'criteria': criteria},
            )

            if response.status_code != 200:
                logger.warning(f'Lead search failed for {email}')
                return []

            data = response.json()
            return data.get('data', [])

    async def update_lead(self, lead_id: str, update_data: Dict) -> Dict:
        """Update an existing lead."""
        token = await self.get_access_token()

        update_payload = {
            'data': [
                {
                    'id': lead_id,
                    **update_data,
                }
            ]
        }

        async with httpx.AsyncClient() as client:
            response = await client.put(
                f'{self.crm_url}/crm/v2/Leads',
                headers={'Authorization': f'Bearer {token}'},
                json=update_payload,
            )

            if response.status_code not in [200, 204]:
                logger.error(f'Lead update failed: {response.text}')
                raise Exception(f'Lead update failed: {response.status_code}')

            logger.info(f'Lead updated: {lead_id}')
            return response.json() if response.text else {'success': True}


class LeadCreationService:
    """High-level service for creating leads with error handling."""

    def __init__(self, crm_client: Optional[ZohoCRMClient] = None):
        self.crm_client = crm_client or ZohoCRMClient()

    async def create_or_update_lead(
        self, lead_data: Dict, max_retries: int = 3
    ) -> Dict:
        """Create a new lead or update if exists, with retry logic.
        
        Args:
            lead_data: Lead information from chatbot
            max_retries: Number of retries on failure
        
        Returns:
            Success/failure response with lead ID
        """
        # First, try to find existing lead by email
        try:
            existing_leads = await self.crm_client.search_leads_by_email(
                lead_data.get('email')
            )
            if existing_leads:
                lead_id = existing_leads[0]['id']
                logger.info(f'Lead exists: {lead_id}, updating...')
                await self.crm_client.update_lead(lead_id, lead_data)
                return {'action': 'updated', 'lead_id': lead_id, 'success': True}
        except Exception as e:
            logger.warning(f'Search failed, will create new: {e}')

        # Create new lead with retry
        for attempt in range(max_retries):
            try:
                result = await self.crm_client.create_lead(lead_data)
                logger.info(f'Lead created successfully: {result}')
                return {'action': 'created', **result, 'success': True}
            except Exception as e:
                logger.error(f'Attempt {attempt + 1} failed: {e}')
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    return {
                        'success': False,
                        'error': str(e),
                        'lead_data': lead_data,
                    }

    async def create_follow_up_task(
        self, lead_id: str, contact_within_hours: int
    ) -> Dict:
        """Create a follow-up task for sales agent."""
        from datetime import timedelta

        due_date = (datetime.now() + timedelta(hours=contact_within_hours)).strftime(
            '%Y-%m-%d'
        )

        task_data = {
            'subject': 'Follow up with lead',
            'description': 'Reach out to prospect regarding their requirements',
            'due_date': due_date,
            'priority': 'High',
        }

        return await self.crm_client.create_task(lead_id, task_data)


# Example usage
if __name__ == '__main__':
    async def test_crm():
        client = ZohoCRMClient()
        service = LeadCreationService(client)

        sample_lead = {
            'first_name': 'Prithivi',
            'last_name': 'Raj',
            'email': 'prithivi@example.com',
            'phone': '+91-9876543210',
            'company': 'Tech Store',
            'business_type': 'E-commerce',
            'lead_score': 78,
            'description': 'Interested in WhatsApp bot for customer support',
        }

        result = await service.create_or_update_lead(sample_lead)
        print(f'Lead result: {result}')

    asyncio.run(test_crm())
