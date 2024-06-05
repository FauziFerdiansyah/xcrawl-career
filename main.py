"""This script serves as an example on how to use Python 
   & Playwright to scrape/extract data from Google Maps"""

from playwright.sync_api import sync_playwright
from dataclasses import dataclass, asdict, field
import pandas as pd
import argparse
import re



keywords = ["career", "careers", "loker", "karir", "join with us", "lowongan kerja", "job opportunity", "job opportunities", "employment", "careers portal", "work with us", "opportunities", "careers section", "employment opportunities", "job vacancies", "work here"]

@dataclass
class Business:
    """holds business data"""

    name: str = None
    address: str = None
    website: str = None
    contain_keyword: str = None
    phone_number: str = None
    reviews_count: int = None
    reviews_average: float = None


@dataclass
class BusinessList:
    """holds list of Business objects,
    and save to both excel and csv
    """

    business_list: list[Business] = field(default_factory=list)

    def deduplicate(self):
      """Remove duplicate entries based on name"""
      unique_names = set()
      unique_businesses = []
      for business in self.business_list:
          if business.name not in unique_names:
              unique_names.add(business.name)
              unique_businesses.append(business)
      self.business_list = unique_businesses


    def dataframe(self):
        """transform business_list to pandas dataframe

        Returns: pandas dataframe
        """
        return pd.json_normalize(
            (asdict(business) for business in self.business_list), sep="_"
        )

    def save_to_excel(self, filename):
        """saves pandas dataframe to excel (xlsx) file"""
        self.deduplicate()  # Remove duplicates before saving
        self.dataframe().to_excel(f"{filename}.xlsx", index=False)

    def save_to_csv(self, filename):
        """saves pandas dataframe to csv file"""
        self.deduplicate()  # Remove duplicates before saving
        self.dataframe().to_csv(f"{filename}.csv", index=False)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto("https://www.google.com/maps?hl=en", timeout=60000)
        # wait is added for dev phase. can remove it in production
        page.wait_for_timeout(5000)

        page.locator('//input[@id="searchboxinput"]').fill(search_for)
        page.wait_for_timeout(3000)

        page.keyboard.press("Enter")
        page.wait_for_timeout(5000)

        # scrolling
        page.hover('//a[contains(@href, "https://www.google.com/maps/place")]')

        # this variable is used to detect if the bot
        # scraped the same number of listings in the previous iteration
        previously_counted = 0
        while True:
            page.mouse.wheel(0, 20000)
            page.wait_for_timeout(3000)

            if (
                page.locator(
                    '//a[contains(@href, "https://www.google.com/maps/place")]'
                ).count()
                >= total
            ):
                listings = page.locator(
                    '//a[contains(@href, "https://www.google.com/maps/place")]'
                ).all()[:total]
                listings = [listing.locator("xpath=..") for listing in listings]
                print(f"🎯 Total Scraped ⟹  {len(listings)}")
                break
            else:
                # logic to break from loop to not run infinitely
                # in case arrived at all available listings
                if (
                    page.locator(
                        '//a[contains(@href, "https://www.google.com/maps/place")]'
                    ).count()
                    == previously_counted
                ):
                    listings = page.locator(
                        '//a[contains(@href, "https://www.google.com/maps/place")]'
                    ).all()
                    print(f"📜 Arrived at all available\nTotal Scraped ⟹ {len(listings)}")
                    break
                else:
                    previously_counted = page.locator(
                        '//a[contains(@href, "https://www.google.com/maps/place")]'
                    ).count()
                    print(
                        f"📜 Currently Scraped ⟹  ",
                        page.locator(
                            '//a[contains(@href, "https://www.google.com/maps/place")]'
                        ).count(),
                    )

        business_list = BusinessList()
        search_number = 1

        # scraping
        for listing in listings:
            listing.click()
            page.wait_for_timeout(5000)

            name_xpath = '//div[contains(@class, "fontHeadlineSmall")]'
            address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
            website_xpath = '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]'
            phone_number_xpath = '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
            reviews_span_xpath = '//span[@role="img"]'

            business = Business()
            print(f"————————————————————————————————————————————————————————————")

            if listing.locator(name_xpath).count() > 0:
                business.name = listing.locator(name_xpath).inner_text()
            else:
                business.name = ""
            print(f"💼 {search_number}). of {len(listings)}  ⟹  {business.name}")
            if page.locator(address_xpath).count() > 0:
                business.address = page.locator(address_xpath).inner_text()
            else:
                business.address = ""
            if page.locator(website_xpath).count() > 0:
                website_url = page.locator(website_xpath).inner_text()

                # Buka website dan cari kata kunci di dalamnya
                try:
                    print(f"🌐 Open website ⟹  {website_url}")
                    new_page = browser.new_page()
                    new_page.goto("http://www." + website_url, timeout=60000)
                    new_page.wait_for_timeout(5000)

                    # Dapatkan konten HTML dari halaman
                    page_content = new_page.content()

                    # Periksa keberadaan kata kunci di konten halaman web
                    keyword_found = False
                    for keyword in keywords:
                        if re.search(r'\b{}\b'.format(keyword), page_content, re.IGNORECASE):
                            keyword_found = True
                            break

                    if keyword_found:
                      print(f"✅ Keyword found on ⟹  {website_url}")
                      new_website = page.locator(website_xpath).inner_text()
                      # business.website = page.locator(website_xpath).inner_text()
                      # Add the business to the list only if the website is present
                      # business_list.business_list.append(business)
                      # Set contain_keyword to "Yes" karena kata kunci ditemukan
                      if not any(business.website == new_website for business in business_list.business_list):
                        # Tambahkan business ke business_list hanya jika website belum ada
                        business.website = new_website
                        business_list.business_list.append(business)
                        business.contain_keyword = "Yes"
                      # Lakukan sesuatu jika kata kunci ditemukan
                    else:
                      print(f"❌ Keyword not found on ⟹  {website_url}")
                      # Set contain_keyword to "No" karena kata kunci tidak ditemukan
                      business.contain_keyword = "No"
                      # if 'new_page' in locals():
                      #   new_page.close()
                except Exception as e:
                    # if 'new_page' in locals():
                    #   new_page.close()
                    print(f"😞 Error while accessing website ⟹  {website_url}")
                    # print(e)
                finally:
                  # Pastikan tab baru ditutup, terlepas dari apakah ada kesalahan atau tidak
                  if 'new_page' in locals():
                    new_page.close()
            else:
                print("⏭️ Website not found for this listing")
                business.website = ""
            if page.locator(phone_number_xpath).count() > 0:
                business.phone_number = page.locator(phone_number_xpath).inner_text()
            else:
                business.phone_number = ""
            if listing.locator(reviews_span_xpath).count() > 0:
                try:
                    reviews_label = listing.locator(reviews_span_xpath).get_attribute("aria-label").strip()
                    reviews_parts = reviews_label.split()
                    reviews_average = reviews_parts[0].replace(",", ".")
                    reviews_count = reviews_parts[2].replace(',', '')
                    business.reviews_average = float(reviews_average)
                    business.reviews_count = int(reviews_count)
                except Exception as e:
                    print(f"😞 Error while extracting reviews information")
                    business.reviews_average = ""
                    business.reviews_count = ""
            else:
                business.reviews_average = ""
                business.reviews_count = ""

            business_list.business_list.append(business)
            search_number += 1

        # saving to both excel and csv just to showcase the features.
        business_list.save_to_excel(f"output/data_{search_for}".replace(' ', '_'))
        business_list.save_to_csv(f"output/data_{search_for}".replace(' ', '_'))

        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--search", type=str)
    parser.add_argument("-t", "--total", type=int)
    args = parser.parse_args()

    if args.search:
        search_for = args.search
    else:
        # in case no arguments passed
        # the scraper will search by defaukt for:
        search_for = "dentist new york"

    # total number of products to scrape. Default is 10
    if args.total:
        total = args.total
    else:
        total = 10

    main()