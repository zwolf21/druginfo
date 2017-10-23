import re, os, time, platform
from datetime import datetime
from urllib.parse import quote, urljoin, unquote
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import OrderedDict
from pprint import pprint


import requests
from bs4 import BeautifulSoup
from listorm import read_excel, read_csv, Listorm
from tqdm import tqdm
import xlrd

try:
    from settings import PUBLIC_IP, HEADERS, USER_ID, PASSWORD, MAX_WORKER
    from shortcuts import hexMD5, ParseWebPage, create_img_html
except:
    from .settings import PUBLIC_IP, HEADERS, USER_ID, PASSWORD, MAX_WORKER
    from .shortcuts import hexMD5, ParseWebPage, create_img_html


class DrugInfoAPI(object):
    host = 'https://www.druginfo.co.kr'
    img_path = '/drugimg/'
    login_url = 'https://www.druginfo.co.kr/login/login.aspx'
    search_url = 'https://www.druginfo.co.kr/search2/search.aspx?q='
    detail_url = 'https://www.druginfo.co.kr/detail/product.aspx?pid='
    MAX_WORKER = 10


    def __init__(self, user_id=None, password=None, public_ip=None, headers=None):
        self.user_id = user_id
        self.password = password
        self.public_ip = public_ip
        self.headers = headers
        self.requests = self.login()
    
    def _get_login_data(self):
        if self.user_id and self.password and self.public_ip:
            timestamp = datetime.now().strftime("%Y%m%d%H")		
            return {
                'id': self.user_id,
                't_passwd': self.password,
                'passwd': hexMD5(timestamp+hexMD5(self.password)+self.public_ip),
                'timestamp': timestamp,
            }
    
    def get(self, url):
        return self.requests.get(url, headers=self.headers)

    def login(self):
        login_data = self._get_login_data()
        if login_data:
            print('Logining for {}...'.format(login_data.get('id')))
            session = requests.Session()
            session.post(self.login_url, login_data, headers=self.headers)
            return session
        return requests

    def logout(self):
        if isinstance(self.requests, requests.Session):
            print('logout complete')
            self.requests.close()
    
    def __del__(self):
        self.logout()
    
    def get_search_list(self, keyword):
        kwd = keyword
        keyword = quote(keyword, encoding='cp949')
        r = self.get(self.search_url+keyword)
        soup = BeautifulSoup(r.content, 'html.parser')
        
        table_titles = []
        product_tables = []

        for subheader in soup('div',{'class':'subheader'}):
            inuse = subheader.text.strip()
            if "유통" in inuse:
                if '유통중인' in inuse:
                    inuse = "유통중"
                else:
                    inuse = "미확인"
                table_titles.append(inuse)

        for table in soup('table'):
            for tr in table('tr'):
                if table('table'):
                    continue
                header = tr.text.strip().split('\n')
                if header == ['제품명', '임부', '보험코드', '판매사', '성분/함량', '구분', '보험', '약가', '조회수', '대체', '수정']:
                    product_tables.append(table)
        
        if len(table_titles) != len(product_tables):
            print('유통 정보와 테이블이 맞지 않습니다')
            return Listorm()
        
        lst_result = Listorm()
        kwd = kwd[:15] + '...' if len(kwd) > 15 else kwd
        for inuse, table in zip(table_titles, product_tables):
            pw = ParseWebPage(str(table))
            lst = Listorm(pw.ext_tables('제품명', '임부', '보험코드', only_data=False))
            lst = lst.add_columns(유통정보=lambda row: inuse, 검색어=lambda row: kwd)
            lst_result += lst
        return lst_result
    
    def get_detail(self, drug_id):
        if not isinstance(self.requests, requests.Session):
            return Listorm()
        record = {'id': drug_id}
        soup = BeautifulSoup(self.get(self.detail_url+drug_id).content, 'html.parser')
        components = [a.text.strip().replace(',','') for a in soup('a', href=re.compile(r'^/ingredient/ingre_view.aspx\?.+$'))]
        record['성분자세히'] = ', '.join(components)
        find = False
        for tr in soup('tr'):
            if tr('tr'):
                continue
            if '복지부분류' in tr.text:
                if tr.td and tr.td.text.strip() == '복지부분류':
                    for td in tr('td'):
                        value = td.text.strip()
                        g = re.search(r'(?P<efcy_code>\d+)\[(?P<efcy_name>.+)\]', value)
                        if not g:
                            continue
                        efcy_code = g.group('efcy_code')
                        efcy_name = g.group('efcy_name')
                        if efcy_code:
                            record['복지부분류코드'] = efcy_code.strip()
                            record['복지부분류'] = efcy_name.strip()
                    break
        
        pw = ParseWebPage(str(soup))
        for elm in pw.ext_tables('항목', '내용'):
            if elm['항목'] in ['포장·유통단위','주성분코드']:
                record[elm['항목']] = elm['내용']
        pkg_str = record.get('포장·유통단위', '')
        componet_code = record.get('주성분코드', '')
        component_code_pattern = re.search(r'(?P<comp_code>[\dA-Z]+)\s+.+', componet_code)
        if component_code_pattern:
            record['주성분코드'] = component_code_pattern.group('comp_code').strip()
        record['포장정보'] = pkg_str or ''
        record['pkg_amount'] = self._pkg_num_from(pkg_str)
        record['마약류구분'] = self._get_narcotic_class(str(soup))
        return record

    def _pkg_num_from(self, pkg_str):
        regx = re.compile('(\d+)정|(\d+)caps?|(\d+)T|(\d+)개|(\d+)바이알|(\d+)캡슐|(\d+)C|(\d+)CAPS|(\d+)|(\d+)EA|(\d+)TAB|(\d+)tab|(\d+)캅셀|(\d+)펜|(\d+)V|(\d+)P|(\d+)포')
        try:
            ret = list(filter(None, regx.findall(pkg_str)[-1]))[0]
            return ret
        except IndexError:
            return '1'

    def _get_narcotic_class(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        mdt = soup('td',{'class':"medi_t2"})
        if mdt:
            for m in mdt:
                if '향정의약품' in m.text:
                    return '향정'
                elif '마약' in m.text:
                    return '마약'
                else:
                    continue
            return '일반'

    def search(self, keyword, detail=False, exclude_ids=None):
        lst = self.get_search_list(keyword)
        id_filter = re.compile(r'/detail/product.aspx\?pid=(?P<drugId>\d+)')
        fda_filter = re.compile(r'^/search2/images/(?P<fda>\w+).gif$')
        exclude = set(exclude_ids or [])
        lst = lst.exclude(where=lambda row: row.id in exclude) 

        def get_drug_id(soup):
            # print(soup)
            for a in soup('a', href=id_filter):
                return id_filter.search(a['href']).group('drugId')
        
        def get_title(soup):
            if soup.a:
                return soup.a.text.strip()
            else:
                return soup.text.strip()
        
        def get_fda(soup):
            for img in soup('img', src=fda_filter):
                g = fda_filter.search(img['src'])
                return g.group('fda') if g else ''
        
        def get_drug_image(soup):
            for a in soup('a', {'class': 'pro-img-link'}):
                _, img = a.text.split(',')
                return urljoin(self.host+self.img_path, img)
            return ''
        
        def norm_price(soup):
            price_str = soup.text.strip() if soup.text else '0'
            regx = re.compile('[^\d]')
            try:
                return int(regx.sub('', price_str))
            except:
                return 0
        
        def get_strip(soup):
            return soup.text.strip() if soup.text else ''
        
        lst = lst.add_columns(
            id=lambda row: get_drug_id(row.제품명),
            price_int= lambda row: norm_price(row.약가),
        ).update(
            제품명=lambda row: get_title(row.제품명),
            임부=lambda row: get_fda(row.임부),
            **{
                '': lambda row: get_drug_image(row['']),
                '보험코드': lambda row: get_strip(row['보험코드']),
                '판매사': lambda row: get_strip(row['판매사']),
                '성분/함량': lambda row: get_strip(row['성분/함량']),
                '구분': lambda row: get_strip(row['구분']),
                '보험': lambda row: get_strip(row['보험']),
                '약가': lambda row: get_strip(row['약가']),
                '조회수': lambda row: get_strip(row['조회수']),
                '대체': lambda row: get_strip(row['대체']),
                '수정': lambda row: get_strip(row['수정']),
            },
        ).rename(**{'': 'img'})
        id_list = lst.column_values('id')

        if id_list and detail:
            if not isinstance(self.requests, requests.Session):
                print('로그인 되지 않았습니다')
                return lst
            with ThreadPoolExecutor(min(self.MAX_WORKER, len(lst))) as executor:
                details = executor.map(self.get_detail, id_list)
                lst_detail = Listorm(details)
                return lst.join(lst_detail, on='id')
        return lst

    def search_one_by_one(self, keywords, **kwargs):
        search_lists = []
        with ThreadPoolExecutor(min(self.MAX_WORKER, len(keywords))) as executor:
            todo_list = []
            for keyword in keywords:
                future = executor.submit(self.search, keyword, **kwargs)
                todo_list.append(future)
            done_iter = tqdm(as_completed(todo_list), total=len(todo_list))
            for future in done_iter:
                search_list = future.result()
                search_lists += search_list
            return search_lists
    
def open_record_file(_file):
    lst = Listorm()
    if not _file:
        return lst
    fn, ext = os.path.splitext(_file)
    if ext in ['.xls','.xlsx']:
        lst = read_excel(_file)
    elif ext =='.csv':
        lst = read_csv(_file)
    return lst 

def query_save_to(user_id, password, keywords, public_ip, headers, _file, start=True, oneByone=True, distinct=True, detail=True, append=None, to_html=None):
    if isinstance(keywords, str):
        keywords = [keywords]
    append_lst = open_record_file(append)
    excludes = append_lst.unique('id') if len(append_lst) > 0 else []

    dg = DrugInfoAPI(user_id, password, public_ip, headers)
    results = []    
    if oneByone:
        results=dg.search_one_by_one(keywords, detail=detail, exclude_ids=excludes)
    else:
        length, step = len(keywords), 50
        todo_range = list(range(0, length, 50))
        iter_range = tqdm(todo_range, total=len(todo_range))

        for page in iter_range:
            keyword = ' '.join(keywords[page: page+step])
            results += dg.search(keyword, detail=detail)

    lst = Listorm(results) + append_lst
    if distinct:
        lst.distinct('id')

    if to_html:
        create_img_html(lst, _file=to_html, start=start)

    if _file or append:
        if start and platform.system() == 'Windows':
            try:
                lst.to_excel(append or _file)
                os.startfile(append or _file)
                return
            except:
                for row in lst:
                    print('Exception Occuer')
                    # print(row)
                return 
        else:
            lst.to_excel(append or _file)

    return lst





