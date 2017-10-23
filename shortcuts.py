import hashlib, re, os, sys
from collections import OrderedDict

from requests import get, Session
from bs4 import BeautifulSoup
import xlrd

def ip42pl():
	return get('http://ip.42.pl/raw').text
	
def jsonip():
	return get('http://jsonip.com').json()['ip']
	
def httpbin():
	return get('http://httpbin.org/ip').json()['origin']
	
def ipify():
	return get('https://api.ipify.org/?format=json').json()['ip']
	
def get_public_ip():
	for f in [httpbin, ip42pl, jsonip, ipify]:
		try:
			ret =  f()
		except Exception as e:
			pass
		else:
			return ret

def hexMD5(value):
	h = hashlib.md5()
	h.update(value.encode())
	return h.hexdigest()


def read_keyword_file(_file):
    if not _file:
        return
    with open(_file) as fp:
        keyword_list = fp.readlines()
        keyword_list = list(map(str.strip, keyword_list))
        return keyword_list

def _float2str(float_val):
    try:
        val = str(int(float_val))
    except Exception as e:
        return float_val
    else:
        return val


def xlspget(xls, pat, distinct=True):
    if xls:
        retPat = []
        p = re.compile(pat)
        for xl in xls:
            wb = xlrd.open_workbook(xl)
            for nsht in range(wb.nsheets):
                sht = wb.sheet_by_index(nsht)
                for r in range(sht.nrows):
                    for c in sht.row(r):
                        edi_str = _float2str(c.value)
                        retPat += p.findall(edi_str)
        if distinct:
            return list(OrderedDict.fromkeys(retPat))
        return retPat

class ParseWebPage(object):
	"""docstring for ParsePage"""
	def __init__(self, content):
		self.soup = BeautifulSoup(content, 'html.parser')

	def show_html(self):
		print(self.soup.text)
		
	def ext_links(self, regPattern, **tagAttr):
		rex = re.compile(regPattern)
		for tag, attr in tagAttr.items():
			qry = '{}[{}]'.format(tag, attr)
			links = self.soup.select(qry)
			return [link for link in links if rex.search(link[attr])]

	def ext_tables(self, *column, only_data=True):
		spc = re.compile('\s+')
		ret = []
		for table in self.soup('table'):
			if table('table'):
				continue
			hdr, *recs = table('tr')
			hdr_val = [spc.sub(' ', hdr.text).strip() for hdr in hdr.select('td, th')]

			if set(column) <= set(hdr_val):
				if only_data:
					ret+=[dict(zip(hdr_val, [spc.sub(' ',rec.text).strip() for rec in rec('td')])) for rec in recs]
				else:
					ret+=[dict(zip(hdr_val, [rec for rec in rec('td')])) for rec in recs]
		return ret


def MakeHTMLTalbe(list_Table, htmlfile = None):
    tbl_tag = '''
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>약품리스트</title>
  <style type="text/css">
    table, th, td {
      border: 1px solid black;
      border-collapse: : collapse;
    }
    th, td {
      padding: 5px;
    }
  </style>
  
<script type="text/javascript">
window.onload=function(){
    var img_insts = document.getElementsByTagName('img');
    var dh = img_insts[0].height;
    var dw = img_insts[0].width;
    var inc = 0.1;
    var scale = 0;
    
    document.getElementById('inc').onclick = function () {
      if (1 + scale > 0) {
          resizeImgs(img_insts,0.1);
      }
    }
    document.getElementById('dsc').onclick = function () {
        resizeImgs(img_insts,-0.1);
    }
    document.getElementById('dflt').onclick = function () {
        for (var i = 0; i < img_insts.length; i++) {
            img_insts[i].height = dh;
            img_insts[i].width = dw;
        }
    }
    function resizeImgs(imgs, ratio) {
        for (var i = 0; i < imgs.length; i++) {
            imgs[i].height += ratio*dh;
            imgs[i].width += ratio*dw;

        }
    }
}
</script>
</head>
    <h1>
        약품 사진
    </h1>
    <input type="button" id="inc" value="사진확대">
    <input type="button" id="dsc" value="사진축소">
    <input type="button" id="dflt" value="기본크기">
<body>
  <table width="100%"><tbody>'''
    for row in list_Table:
        tbl_tag += "<tr>"
        for data in row:
            tbl_tag += "<td>{}</td>".format(str(data))
        tbl_tag += "</tr>\r\n"
    tbl_tag += "</tbody></table></body></html>"
    soup = BeautifulSoup(tbl_tag,"html.parser")
    tbl_tag = soup.prettify('utf-8')
    if htmlfile:
        with open(htmlfile,'wb') as fp:
            fp.write(tbl_tag)
    return tbl_tag


def create_img_html(lst, _file='약품사진.html',start=False):
    table = []
    col = []
    lst.orderby('제품명')
    for row in lst:
        img_src = row['img']
        drug_name = row['제품명']
        data = '''<div><img src="{}" width="150" height="81" border="0" alt="실제이미지"></div>
        <font style="font-size:larger; color:Black; font-weight:bold;"><br>{}</font>'''.format(img_src, drug_name)
        col.append(data)

    tab = 4

    for i in range(0,len(col),tab):
        table.append(tuple(col[i:i+tab]))

    MakeHTMLTalbe(table, _file)
    if start and platform.system() == 'Windows':
        os.startfile(_file)