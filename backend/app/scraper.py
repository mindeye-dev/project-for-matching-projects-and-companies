from apscheduler.schedulers.background import BackgroundScheduler

def scrape_all_sources():
    # TODO: Implement scraping logic for all banks/donors
    print('Scraping all sources...')
 
scheduler = BackgroundScheduler()
scheduler.add_job(scrape_all_sources, 'interval', days=1)
scheduler.start() 