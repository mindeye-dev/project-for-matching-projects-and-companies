#!/usr/bin/env python3
"""
Quick script to run the World Bank scraper immediately for testing.
Usage: python run_scraper_now.py
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scheduled_scraper import scrape_world_bank

if __name__ == "__main__":
    print("Running World Bank scraper immediately...")
    scrape_world_bank()
    print("Scraping completed!") 