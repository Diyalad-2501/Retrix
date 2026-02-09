#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test script for SKU analysis page"""

import sys
import os
sys.path.insert(0, os.getcwd())

from app import app, db, Seller, CSVUpload

# First check if CSV file exists
csv_path = 'uploads/4_sample_ecommerce_orders.csv'
print('CSV file exists:', os.path.exists(csv_path))

with app.app_context():
    # Create test data
    if not Seller.query.first():
        seller = Seller(
            name='Test Seller',
            store_name='Test Store',
            email='test@example.com',
            password='testpassword',
            unique_code='TEST01',
            profile_icon='fa-user'
        )
        db.session.add(seller)
        db.session.commit()
        print('Created test seller')
    
    # Create test upload
    if not CSVUpload.query.first():
        upload = CSVUpload(
            user_id=1,
            seller_id=1,
            filename='test_orders.csv',
            original_name='test_orders.csv',
            filepath=csv_path,
            row_count=100
        )
        db.session.add(upload)
        db.session.commit()
        print('Created test upload')

# Test with Flask test client
with app.test_client() as client:
    # Set session
    with client.session_transaction() as sess:
        sess['seller_id'] = 1
        sess['seller_name'] = 'Test Seller'
        sess['selected_csv_path'] = csv_path
    
    # Test routes
    print('Testing /sku-analysis...')
    response = client.get('/sku-analysis')
    print('Status code:', response.status_code)
    if response.status_code == 200:
        print('SUCCESS: SKU Analysis page loaded')
        content = response.data.decode()
        print('HTML length:', len(content))
        # Check if it's the right page
        if 'SKU Analysis' in content:
            print('Found SKU Analysis title')
        if 'Retrix' in content:
            print('Found Retrix branding')
    else:
        print('FAILED:', response.data.decode()[:500])
