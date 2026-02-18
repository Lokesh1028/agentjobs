"""Real job scraper - LinkedIn public pages. No login needed."""
import aiohttp, asyncio, json, re, hashlib, sqlite3, logging
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
logger = logging.getLogger(__name__)

SEARCH_QUERIES = [
    ("ML data associate", "India"), ("data annotation AI", "India"),
    ("data scientist", "Hyderabad"), ("data scientist", "Bangalore"),
    ("data scientist", "Mumbai"), ("data scientist", "Pune"),
    ("data analyst", "Hyderabad"), ("data analyst", "Bangalore"),
    ("machine learning engineer", "India"), ("computer vision engineer", "India"),
    ("AI engineer", "India"), ("data engineer", "Hyderabad"),
    ("data engineer", "Bangalore"), ("software engineer", "Hyderabad"),
    ("software engineer", "Bangalore"), ("software engineer", "Mumbai"),
    ("backend developer python", "India"), ("frontend developer react", "India"),
    ("full stack developer", "Hyderabad"), ("full stack developer", "Bangalore"),
    ("java developer", "India"), ("python developer", "India"),
    ("devops engineer", "India"), ("cloud engineer AWS", "India"),
    ("android developer", "India"), ("flutter developer", "India"),
    ("product manager", "Bangalore"), ("UX designer", "India"),
    ("cybersecurity analyst", "India"), ("QA engineer", "India"),
    ("business analyst", "Hyderabad"), ("business analyst", "Bangalore"),
    ("scrum master", "India"), ("technical writer", "India"),
    ("remote software engineer", "India"), ("remote data scientist", "India"),
    ("golang developer", "India"), ("kubernetes engineer", "India"),
    ("react developer", "India"), ("nodejs developer", "India"),
    ("site reliability engineer", "India"), ("SDET", "India"),
    ("product manager", "Hyderabad"), ("security engineer", "India"),
]

def gen_jid(src, sid):
    return f"j_{hashlib.md5(f'{src}:{sid}'.encode()).hexdigest()[:12]}"

def gen_cid(name):
    return f"c_{hashlib.md5(re.sub(r'[^a-z0-9]','',name.lower()).encode()).hexdigest()[:10]}"

def parse_time(text):
    text = text.strip().lower()
    now = datetime.utcnow()
    if "just now" in text: return now.isoformat()+"Z"
    m = re.search(r'(\d+)\s*(second|minute|hour|day|week|month)', text)
    if m:
        n, u = int(m.group(1)), m.group(2)
        d = {"second":timedelta(seconds=n),"minute":timedelta(minutes=n),"hour":timedelta(hours=n),
             "day":timedelta(days=n),"week":timedelta(weeks=n),"month":timedelta(days=n*30)}
        for k,v in d.items():
            if u.startswith(k): return (now-v).isoformat()+"Z"
    return None

def guess_skills(title):
    t = title.lower(); skills = []
    mp = {"python":["python"],"java ":["java"],"react":["react","javascript"],"node":["nodejs"],
          "golang":["golang"],"go ":["golang"],"docker":["docker"],"kubernetes":["kubernetes"],
          "aws":["aws","cloud"],"azure":["azure","cloud"],"gcp":["gcp","cloud"],
          "devops":["devops","ci-cd"],"machine learning":["machine-learning","python"],
          "ml ":["machine-learning","python"],"deep learning":["deep-learning","python"],
          "nlp":["nlp","python"],"computer vision":["computer-vision","python"],
          "data scien":["python","sql","machine-learning"],"data analy":["python","sql","excel"],
          "data engineer":["python","sql","spark"],"data annot":["data-annotation"],
          "frontend":["html","css","javascript"],"backend":["api","databases"],
          "full stack":["javascript","api"],"android":["kotlin","android"],
          "ios":["swift","ios"],"flutter":["flutter","dart"],"security":["cybersecurity"],
          "qa":["testing"],"sdet":["testing","automation"],"product manager":["product-management"],
          "ux":["ux-design","figma"],"ui":["ui-design","figma"],"terraform":["terraform"],
          "rust":["rust"],"c++":["c++"],".net":[".net","c#"]}
    for kw,sk in mp.items():
        if kw in t: skills.extend(sk)
    return list(set(skills))

def guess_cat(title):
    t = title.lower()
    cats = {"data-science":["data scien","machine learning","ml ","deep learning","nlp","computer vision","ai ","data annot"],
            "engineering":["software","developer","engineer","backend","frontend","full stack","devops","sre","cloud","golang","flutter","react native","embedded"],
            "design":["designer","ux","ui ","product design"],"product":["product manager","product owner"],
            "qa":["qa ","quality","sdet","test"],"security":["security","cyber","penetration"],
            "operations":["project manager","scrum","delivery"],"content":["writer","content","documentation"]}
    for cat,kws in cats.items():
        for kw in kws:
            if kw in t: return cat
    return "engineering"

async def scrape_linkedin(query, location, session):
    url = f"https://www.linkedin.com/jobs/search/?keywords={query.replace(' ','%20')}&location={location.replace(' ','%20')}&f_TPR=r2592000"
    headers = {"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
               "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8","Accept-Language":"en-US,en;q=0.5"}
    jobs = []
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200: return []
            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")
            for card in soup.find_all("li"):
                try:
                    link = card.find("a", href=re.compile(r"/jobs/view/"))
                    if not link: continue
                    href = link.get("href","")
                    if "/jobs/view/" not in href: continue
                    jid_m = re.search(r'(\d{8,})', href)
                    if not jid_m: continue
                    ljid = jid_m.group(1)
                    clean_url = re.sub(r'\?.*$','',href)
                    if not clean_url.startswith("http"): clean_url = "https://www.linkedin.com" + clean_url
                    
                    title_el = card.find("h3") or card.find("span", class_=re.compile(r"title"))
                    title = title_el.get_text(strip=True) if title_el else link.get_text(strip=True)
                    title = re.sub(r'\s+',' ',title).strip()
                    if not title or len(title)<3 or len(title)>200: continue
                    
                    comp_el = card.find("h4") or card.find("a", class_=re.compile(r"company|subtitle"))
                    if not comp_el: comp_el = card.find("span", class_=re.compile(r"subtitle|company"))
                    company = comp_el.get_text(strip=True) if comp_el else None
                    if not company or len(company)<2: continue
                    
                    loc_el = None
                    for s in card.find_all("span"):
                        txt = s.get_text(strip=True)
                        if any(c in txt for c in ["Hyderabad","Bangalore","Bengaluru","Mumbai","Pune","Chennai","Delhi","Kolkata","India","Remote","Noida","Gurugram","Karnataka","Telangana","Maharashtra"]):
                            loc_el = s; break
                    job_loc = loc_el.get_text(strip=True) if loc_el else location
                    
                    time_el = card.find("time")
                    posted = parse_time(time_el.get_text(strip=True)) if time_el else datetime.utcnow().isoformat()+"Z"
                    
                    jobs.append({"id":gen_jid("linkedin",ljid),"title":title,"company_name":company,
                        "company_id":gen_cid(company),"location":job_loc,
                        "location_type":"remote" if "remote" in (title+job_loc).lower() else "onsite",
                        "skills":json.dumps(guess_skills(title)),"category":guess_cat(title),
                        "employment_type":"full-time","apply_url":clean_url,
                        "source":"linkedin","source_id":ljid,"posted_at":posted,
                        "description_short":f"Join {company} as a {title}. Location: {job_loc}."})
                except: continue
    except asyncio.TimeoutError: logger.warning(f"Timeout: {query}")
    except Exception as e: logger.error(f"Error: {e}")
    return jobs

async def run_full_scrape(db_path="agentjobs.db"):
    all_jobs, all_companies, seen = [], {}, set()
    connector = aiohttp.TCPConnector(limit=3)
    async with aiohttp.ClientSession(connector=connector) as session:
        for i,(q,loc) in enumerate(SEARCH_QUERIES):
            logger.info(f"[{i+1}/{len(SEARCH_QUERIES)}] Scraping: '{q}' in {loc}")
            jobs = await scrape_linkedin(q, loc, session)
            for j in jobs:
                if j["id"] not in seen:
                    seen.add(j["id"]); all_jobs.append(j)
                    cid = j["company_id"]
                    if cid not in all_companies:
                        all_companies[cid] = {"id":cid,"name":j["company_name"]}
            logger.info(f"  Found {len(jobs)}, total unique: {len(all_jobs)}")
            await asyncio.sleep(1.5)
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    for comp in all_companies.values():
        c.execute("INSERT OR IGNORE INTO companies (id, name, created_at, updated_at) VALUES (?,?,?,?)",
                  (comp["id"], comp["name"], now, now))
    for j in all_jobs:
        c.execute("""INSERT OR REPLACE INTO jobs (id,company_id,title,description_short,location,location_type,
                     skills,category,employment_type,apply_url,source,source_id,posted_at,scraped_at,is_active)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (j["id"],j["company_id"],j["title"],j["description_short"],j["location"],j["location_type"],
                   j["skills"],j["category"],j["employment_type"],j["apply_url"],j["source"],j["source_id"],
                   j["posted_at"],now,True))
    conn.commit()
    try:
        c.execute("DELETE FROM jobs_fts")
        c.execute("""INSERT INTO jobs_fts(job_id,title,description,skills,location,company_name)
                     SELECT j.id,j.title,COALESCE(j.description,''),COALESCE(j.skills,''),
                     COALESCE(j.location,''),COALESCE(co.name,'') FROM jobs j LEFT JOIN companies co ON j.company_id=co.id""")
        conn.commit()
    except Exception as e: logger.warning(f"FTS: {e}")
    conn.close()
    return {"total_jobs":len(all_jobs),"total_companies":len(all_companies),"queries_run":len(SEARCH_QUERIES)}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = asyncio.run(run_full_scrape())
    print(f"\nDone! Jobs: {result['total_jobs']}, Companies: {result['total_companies']}")
