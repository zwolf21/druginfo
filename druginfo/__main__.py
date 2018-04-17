import re, os, time, argparse, platform, getpass

try:
    from druginfo import query_save_to
    from settings import USER_ID, PASSWORD, PUBLIC_IP, HEADERS
    from shortcuts import xlspget, read_keyword_file
except:
    from .druginfo import query_save_to
    from .settings import USER_ID, PASSWORD, PUBLIC_IP, HEADERS
    from .shortcuts import xlspget, read_keyword_file



def main():
    argparser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter, description="드럭인포 유틸")
    argparser.add_argument('keywords', help='검색할 키워드들 나열', nargs='*')
    argparser.add_argument('-d', '--detail', help='자세한 정보 표시', action='store_true', default=False)
    argparser.add_argument('-p', '--precision', help='검색어 일일이 하나씩 검색하기(검색 실패도 결과에 포함)', action='store_true', default=False)
    argparser.add_argument('-P', '--Precision', help='검색어 일일이 하나씩 검색하기(검색 실패도 결과에 포함, 중복 약품 제거)', action='store_true', default=False)
    argparser.add_argument('-o', '--output', help='검색 결과 엑셀파일로 저장',  nargs='?')
    argparser.add_argument('-O', '--Output', help='검색 결과 엑셀파일로 저장 후 열기',  nargs='?')
    argparser.add_argument('-I', '--Image', help='약품 사진 주출(HTML) 후 열기',  nargs='?')
    argparser.add_argument('-i', '--image', help='약품 사진 주출(HTML)',  nargs='?')
    argparser.add_argument('-a', '--append', help='엑셀파일에 저장할 경우 기존항목 추가')
    argparser.add_argument('-A', '--Append', help='엑셀파일에 저장할 경우 기존항목 추가 후 열기')
    argparser.add_argument('-f', '--file', help='키워드 리스트 있는 파일전달')
    argparser.add_argument('-x', '--excel', help='엑셀 파일에서 EDI코드 찾아내어 검색하기', nargs='+')

    args = argparser.parse_args()

    user_id, password = USER_ID, PASSWORD
    if not user_id and not password and args.detail:
        user_id = input('드럭인포 아이디 입력: ')
        password = getpass.getpass('비밀번호: ')

    print(args)
    query_save_to(
        user_id = user_id, password = password, public_ip=PUBLIC_IP, headers=HEADERS,
        keywords = xlspget(args.excel, '[A-Z\d]\d{8}') or read_keyword_file(args.file) or args.keywords,
        _file = args.output or args.Output or args.append or args.Append, 
        start = args.Image or args.Output or args.Append,
        oneByone = args.precision or args.Precision,
        distinct = args.Precision,
        detail = args.detail,
        append = args.append or args.Append,
        to_html = args.Image or args.image
    )


if __name__ == '__main__':
    main()