def check_flight():
    URL="https://www.google.com/flights/explore/#explore;f=JFK,EWR,LGA;t=HND,NRT,TPE,HKG,KIX;s=1;li=8;lx=12;d=2018-06-01"

    PJS_PATH ="C:\\Users\\Jihye Lee\\Desktop\\phantomjs-2.1.1-windows\\phantomjs-2.1.1-windows\\bin\\phantomjs.exe"
    driver = webdriver.PhantomJS(PJS_PATH)
    dcap = dict(DesiredCapabilities.PHANTOMJS)
    dcap["phantomjs.page.settings.userAgent"] = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36")
    
    driver = webdriver.PhantomJS(desired_capabilities=dcap, executable_path=PJS_PATH)
    driver.implicitly_wait(20)
    driver.get(url)
    
    wait = WebDriverWait(driver, 20)
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "span.CTPFVNB-v-c")))
    
    s = BeautifulSoup(driver.page_source, "lxml")
    
    best_price_tags = s.find_all('div', 'CTPFVNB-w-e')
    
    # 데이터 가져오기 확인 - 실패 또는 중지 시 경고
    if len(best_price_tags) < 4:
        print('Failed to Load Page Data')
        requests.post('https://maker.ifttt.com/trigger/fare_alert/with/key/pR1zp_YyHL7U_HiDBwtJDYVOEpQDF3cJxIEDj5AM7dN',
                      data={ "value1" : "script", "value2" : "failed", "value3" : "" })
        sys.exit(0)
    else:
        print('Successfully Loaded Page Data')
    
    best_prices = []
    for tag in best_price_tags:
        best_prices.append(int(tag.text.replace('$','').replace(',','')))        
    best_price = best_prices[0]
    
    best_height_tags = s.find_all('div', 'CTPFVNB-w-f')
    best_heights = []
    for tag in best_height_tags:
        best_heights.append(float(tag.attrs['style'].split('height:')[1].replace('px;','')))
    best_height = best_heights[0]
    
    # 높이(픽셀) 대비 가격
    pph = np.array(best_price)/np.array(best_height)
    cities = s.findAll('div', 'CTPFVNB-w-o')
    hlist=[]
    for bar in cities[0].findAll('div', 'CTPFVNB-w-x'):
        hlist.append(float(bar['style'].split('height: ')[1].replace('px;',''))*pph)

    fares = pd.DataFrame(hlist, columns = ['price'])
    px = [x for x in fares['price']]
    ff = pd.DataFrame(px, columns = ['fare']).reset_index()
    
    # 클러스터링 시작
    X = StandardScaler().fit_transform(ff)
    db = DBSCAN(eps = 0.45, min_samples = 1).fit(X)

    labels = db.labels_
    clusters = len(set(labels))
    
    pf = pd.concat([ff, pd.DataFrame(db.labels_, columns = ['cluster'])], axis = 1)
    rf = pf.groupby('cluster'['fare'].agg(['min', 'count']).sort_values('min', scending = True))
    
    # 규칙설정
    # 2개 이상 클러스터 필수
    # 클러스터의 최솟값이 최저가와 동일해야 함
    # 클러스터의 사이즈는 1/10 미만
    # 클러스터는 다음으로 낮은 요금의 클러스터 보다 100달러 더 낮아야 함
    if clusters >1 and ff['fare'].min() == rf.iloc[0]['min'] and rf.iloc[0]['count'] < rf['count'].quantile(.10) and rf.iloc[0]['fare'] + 100 < rf.iloc[1]['fare']:
        city = s.find('span', 'CTPFVNB-v-c').text
        fare = s.find('div', 'CTPFVNB-w-e').text
        requests.post('https://maker.ifttt.com/trigger/fare_alert/with/key/pR1zp_YyHL7U_HiDBwtJDYVOEpQDF3cJxIEDj5AM7dN',
                      data={ "value1" : "city", "value2" : "fare", "value3" : "" })
    else:
        print('no alert triggered')
        
    # 코드가 매 60분마다 수행되도록 스케줄러 설정
    schedule.every(60).minutes.do(check_flights)

    while 1:
        schedule.run_pending()
        time.sleep(1)  
        
