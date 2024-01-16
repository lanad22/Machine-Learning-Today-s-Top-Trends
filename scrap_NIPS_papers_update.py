import datetime as dt
import json
import bs4
import httpx
import tqdm
import pandas as pd

urlroot = "https://papers.nips.cc"

limits = httpx.Limits(max_keepalive_connections=4, max_connections=8)

def add_abstract_to_paper_with_client(paper, client):
    text = client.get(paper["url"]).text
    page = bs4.BeautifulSoup(text, "html.parser")
    try:
        ps = page.find("h4", string="Abstract").find_next_siblings("p")
        abstract = "\n".join(p.text for p in ps).strip()
    except AttributeError:
        abstract = ""
    return {**paper, **{"abstract": abstract}}

def get_paper_from_li(bullet):
    titlelink = bullet.find_next("a")
    url = urlroot + titlelink.attrs["href"]
    title = titlelink.text
    authors = [a.strip() for a in bullet.find_next("i").text.split(",")]
    return {"title": title, "authors": authors, "url": url}

def get_papers_from_url(url):
    r = httpx.get(url)
    r.raise_for_status()
    page = bs4.BeautifulSoup(r.text, "html.parser")
    papers = [get_paper_from_li(li) for li in page.find("div", "container-fluid").find_all("li")]
    return papers

def get_year(year):
    papers = get_papers_from_url(f"{urlroot}/paper/{str(year)}")
    for paper in papers:
        paper["year"] = year
    with httpx.Client(timeout=None, limits=limits) as client:
        papers_with_abstracts = [add_abstract_to_paper_with_client(paper, client) for paper in papers]
    print(f"Scraped data for year {year}")
    return papers_with_abstracts

def get_all_years(last_year=None):
    if last_year is None:
        last_year = dt.datetime.now().year - 1
    years = []
    for year in range(1987, last_year + 1):
        try:
            year_data = get_year(year)
            years.extend(year_data)
        except Exception as e:
            print(f"No data found for year {year}: {e}")
            continue
    return years

def extract_metadata(papers):
    metadata = []
    for paper in papers:
        metadata.append({
            "Title": paper["title"],
            "Authors": ", ".join(paper["authors"]),
            "Year": paper["year"],
            "Abstract": paper["abstract"]
        })
    return metadata

papers = get_all_years()
metadata = extract_metadata(papers)
df = pd.DataFrame(metadata)
df.to_csv("papers_2.csv", index=False)
