import os
import time
import requests
import logging
import asyncio

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

import concurrent.futures

import threading

stop_event = threading.Event()


# Import individual scrapers
from app.scrapers_of_projects.bank_scraper_wb import WorldBankScraper
from app.scrapers_of_projects.bank_scraper_afdb import AfricanDevelopmeBankScraper
from app.scrapers_of_projects.bank_scraper_eib import EuropeanInvestmentBankScraper
from app.scrapers_of_projects.bank_scraper_afd import FrenchDevelopmentAgencyScraper
from app.scrapers_of_projects.bank_scraper_kfw import KfWEntwicklungsBankScraper
from app.scrapers_of_projects.bank_scraper_undp import UnitedNationsDevelopmentProgrammeScraper
from app.scrapers_of_projects.bank_scraper_adb import AsianDevelopmentBankScraper
from app.scrapers_of_projects.bank_scraper_ebrd import EuropeanBankScraper
from app.scrapers_of_projects.bank_scraper_ifc import InternationalFinanceCorporationScraper
from app.scrapers_of_projects.bank_scraper_fmo import DutchEnterpreneurialDevelopmentBankScraper
from app.scrapers_of_projects.bank_scraper_miga import WorldBankGroupGuaranteesScraper
from app.scrapers_of_projects.bank_scraper_iadb import InterAmericanDevelopmentBankScraper
from app.scrapers_of_projects.bank_scraper_debit import DevelopmentBankScraper


# Global Lock to ensure that only one scraping process runs at a time
scraping_lock = threading.Lock()

# --- Config ---
BACKEND_API = os.environ.get("BACKEND_API", "http://localhost:5000/api/opportunity")
PROXY_API_KEY = os.environ.get("PROXY_API_KEY", "")
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK", "")
HEADLESS = os.environ.get("HEADLESS", "1") == "1"

# --- Logging ---
logging.basicConfig(
    filename="scheduled_scraper.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(message)s",
)


def notify_error(message):
    if SLACK_WEBHOOK:
        try:
            requests.post(SLACK_WEBHOOK, json={"text": message})
        except Exception as e:
            logging.error(f"Failed to send Slack notification: {e}")





# def start_scheduler():
#     """Start the scheduler for daily runs"""
#     scheduler = BackgroundScheduler()

#     # Schedule scrapers at different times to avoid conflicts
#     # World Bank at 9:00 AM
#     scheduler.add_job(
#         scrape_wb,
#         CronTrigger(hour=9, minute=0),
#         id="daily_world_bank_scrape",
#         name="Daily World Bank Scrape",
#         replace_existing=True,
#     )

#     # African Development Bank at 9:30 AM
#     scheduler.add_job(
#         scrape_afdb,
#         CronTrigger(hour=9, minute=30),
#         id="daily_african_development_bank_scrape",
#         name="Daily African Development Bank Scrape",
#         replace_existing=True,
#     )

#     # European Investment Bank at 10:00 AM
#     scheduler.add_job(
#         scrape_eib,
#         CronTrigger(hour=10, minute=00),
#         id="daily_european_investment_bank_scrape",
#         name="Daily European Investment Bank Scrape",
#         replace_existing=True,
#     )

#     # Agence Française de Développement at 10:30 AM
#     scheduler.add_job(
#         scrape_afd,
#         CronTrigger(hour=10, minute=30),
#         id="daily_agence_française_de_développement_scrape",
#         name="Daily Française de Développement Scrape",
#         replace_existing=True,
#     )

#     # Islamic Development Bank at 11:00 AM
#     scheduler.add_job(
#         scrape_isdb,
#         CronTrigger(hour=11, minute=00),
#         id="daily_islamic_development_bank_scrape",
#         name="Daily Islamic Development Bank Scrape",
#         replace_existing=True,
#     )

#     # Kfw Development Bank at 11:30 AM
#     scheduler.add_job(
#         scrape_kfw,
#         CronTrigger(hour=11, minute=30),
#         id="daily_kfw_development_bank_scrape",
#         name="Daily Kfw Development Bank Scrape",
#         replace_existing=True,
#     )

#     # United Nations Development Programme at 12:00 AM
#     scheduler.add_job(
#         scrape_undp,
#         CronTrigger(hour=12, minute=00),
#         id="daily_united_nations_developmnet_programme_scrape",
#         name="Daily United Nations Development Programme Scrape",
#         replace_existing=True,
#     )

#     # Asian Development Bank at 12:30 AM
#     scheduler.add_job(
#         scrape_adb,
#         CronTrigger(hour=12, minute=30),
#         id="daily_asian_development_bank_scrape",
#         name="Daily Asian Development Bank Scrape",
#         replace_existing=True,
#     )

#     # European Bank for Reconstruction & Development at 13:00 AM
#     scheduler.add_job(
#         scrape_ebrd,
#         CronTrigger(hour=13, minute=00),
#         id="daily_european_bank_for_reconstruction_development_scrape",
#         name="Daily European Bank for Reconstruction & Development Scrape",
#         replace_existing=True,
#     )

#     # International Finance Corporation(IFC) at 13:30 AM
#     scheduler.add_job(
#         scrape_ifc,
#         CronTrigger(hour=13, minute=30),
#         id="daily_international_finance_corporation_scrape",
#         name="Daily International Finance Corporation Scrape",
#         replace_existing=True,
#     )
#     # FMO at 14:00 AM
#     scheduler.add_job(
#         scrape_fmo,
#         CronTrigger(hour=14, minute=00),
#         id="daily_fmo_scrape",
#         name="Daily FMO Scrape",
#         replace_existing=True,
#     )

#     # Multilateral Investment Guarantee Agency(MIGA) at 14:30 AM
#     scheduler.add_job(
#         scrape_miga,
#         CronTrigger(hour=14, minute=30),
#         id="daily_multilateral_investment_guarantee_agency_scrape",
#         name="Multilateral Investment Guarantee Agency Scrape",
#         replace_existing=True,
#     )

#     # Inter American Development Bank at 15:00 AM
#     scheduler.add_job(
#         scrape_idb,
#         CronTrigger(hour=15, minute=00),
#         id="daily_inter_american_development_bank_scrape",
#         name="Daily Inter American Development Bank Scrape",
#         replace_existing=True,
#     )

#     # DeBIT Database at 15:30 AM
#     scheduler.add_job(
#         scrape_debit,
#         CronTrigger(hour=15, minute=30),
#         id="daily_debit_database_scrape",
#         name="Daily DeBIT Database Scrape",
#         replace_existing=True,
#     )

#     scheduler.start()
#     logging.info("Scheduler started. Daily scrapes scheduled:")
#     logging.info("- World Bank: 9:00 AM")
#     logging.info("- African Development Bank: 9:30 AM")
#     logging.info("- European Investment Bank: 10:00 AM")
#     logging.info("- Agence Française de Développement: 10:30 AM")
#     logging.info("- Islamic Development Bank: 11:00 AM")
#     logging.info("- Kfw Development Bank: 11:30 AM")
#     logging.info("- United Nations Development Programme: 12:00 AM")
#     logging.info("- Asian Development Bank: 12:30 AM")
#     logging.info("- European Bank for Reconstruction & Development: 13:00 AM")
#     logging.info("- International Finance Corporation: 13:30 AM")
#     logging.info("- FMO: 14:00 AM")
#     logging.info("- Multilateral Investment Guarantee Agency: 14:30 AM")
#     logging.info("- Inter American Development Bank: 15:00 AM")
#     logging.info("- DeBIT Database: 15:30 AM")

#     try:
#         while True:
#             time.sleep(60)
#     except (KeyboardInterrupt, SystemExit):
#         scheduler.shutdown()
#         logging.info("Scheduler stopped.")


async def run_scraping():
    with scraping_lock:
        # List of scraping functions
        scrape_wb = WorldBankScraper()
        scrape_afdb = AfricanDevelopmeBankScraper()
        scrape_eib = EuropeanInvestmentBankScraper()
        scrape_afd = FrenchDevelopmentAgencyScraper()
        scrape_kfw = KfWEntwicklungsBankScraper()
        scrape_undp = UnitedNationsDevelopmentProgrammeScraper()
        scrape_adb = AsianDevelopmentBankScraper()
        scrape_ebrd = EuropeanBankScraper()
        scrape_ifc = InternationalFinanceCorporationScraper()
        scrape_fmo = DutchEnterpreneurialDevelopmentBankScraper()
        scrape_miga = WorldBankGroupGuaranteesScraper()
        scrape_iadb = InterAmericanDevelopmentBankScraper()
        #scrape_debit = DevelopmentBankScraper()
        scrapers = [
            scrape_wb,
            # scrape_afdb,
            # scrape_eib,
            # scrape_afd,
            # scrape_isdb,
            # scrape_kfw,
            # scrape_undp,
            # scrape_adb,
            # scrape_ebrd,
            # scrape_ifc,
            # scrape_fmo,
            # scrape_miga,
            # scrape_iadb,
            # scrape_debit,
        ]
        # with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        #     future_to_scraper = {executor.submit(scraper): scraper for scraper in scrapers}
        #     for future in concurrent.futures.as_completed(future_to_scraper):
        #         scraper = future_to_scraper[future]
        #         try:
        #             future.result()
        #         except Exception as e:
        #             logging.error(f"Error running {scraper.__name__}: {e}")
        #             notify_error(f"Error running {scraper.__name__}: {e}")

        # await scrape_adb.scrape_page()


def stop_scraping():
    stop_event.set()  # signals all scrapers to stop


if __name__ == "__main__":
    asyncio.run(run_scraping())
