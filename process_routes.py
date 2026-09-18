import geopandas as gpd
from shapely.geometry import Point

print(">> 데이터 로딩 중...")
routes = gpd.read_file('routes.geojson')
if routes.crs is None:
    routes.set_crs(epsg=4326, inplace=True)

# 전국 시군구 경계
kor_url = "https://raw.githubusercontent.com/southkorea/southkorea-maps/master/kostat/2018/json/skorea-municipalities-2018-geo.json"
kor_gdf = gpd.read_file(kor_url).to_crs(epsg=4326)

# 전 세계 국가 경계
world_url = "https://d2ad6b4ur7yvpq.cloudfront.net/naturalearth-3.3.0/ne_110m_admin_0_countries.geojson"
world_gdf = gpd.read_file(world_url).to_crs(epsg=4326)

KOR_SIDO_CODE_MAP = {
    "11": "서울특별시", "21": "부산광역시", "22": "대구광역시", "23": "인천광역시",
    "24": "광주광역시", "25": "대전광역시", "26": "울산광역시", "29": "세종특별자치시",
    "31": "경기도", "32": "강원특별자치도", "33": "충청북도", "34": "충청남도",
    "35": "전북특별자치도", "36": "전라남도", "37": "경상북도", "38": "경상남도", "39": "제주특별자치도"
}

COUNTRY_MAP = {
    "Japan": "일본", "Taiwan": "대만", "United States": "미국", "United States of America": "미국",
    "Vietnam": "베트남", "China": "중국", "Thailand": "태국", "Singapore": "싱가포르",
    "Hong Kong": "홍콩", "United Kingdom": "영국", "France": "프랑스", "Germany": "독일",
    "Italy": "이탈리아", "Canada": "캐나다", "Australia": "호주"
}

kor_gdf['sido_name'] = kor_gdf['code'].str[:2].map(KOR_SIDO_CODE_MAP).fillna("기타시도")

print(">> 공간 교차 연산 수행 중...")
joined = gpd.sjoin(routes, kor_gdf[['name', 'sido_name', 'geometry']], how='left', predicate='intersects')

grouped = joined.groupby(joined.index).agg({
    'sido_name': lambda x: list(set(x.dropna())),
    'name_right': lambda x: list(set(x.dropna()))
})

routes['country'] = "대한민국"
routes['sido'] = ""
routes['sigungu'] = ""

for idx, row in routes.iterrows():
    coords = list(row.geometry.coords)
    first_pt = Point(coords[0])
    lng, lat = first_pt.x, first_pt.y
    
    # 1. 대한민국 외 영역
    if not (124.0 <= lng <= 132.0 and 33.0 <= lat <= 38.9):
        if 122.5 <= lng <= 154.0 and 24.0 <= lat <= 46.0:
            routes.at[idx, 'country'] = "일본"
        else:
            c_name = "해외"
            for _, w_row in world_gdf.iterrows():
                if w_row.geometry.contains(first_pt):
                    raw_c = w_row.get('name') or w_row.get('ADMIN') or "해외"
                    c_name = COUNTRY_MAP.get(raw_c, raw_c)
                    break
            routes.at[idx, 'country'] = c_name
        routes.at[idx, 'sido'] = "-"
        routes.at[idx, 'sigungu'] = "-"
    else:
        # 2. 대한민국 내 영역
        routes.at[idx, 'country'] = "대한민국"
        sidos = grouped.loc[idx, 'sido_name'] if idx in grouped.index else []
        sigs = grouped.loc[idx, 'name_right'] if idx in grouped.index else []
        
        # 해안선 완충 (제주항 등)
        if not sidos:
            if 33.1 <= lat <= 33.6 and 126.1 <= lng <= 127.0:
                sidos = ["제주특별자치도"]
                sigs = ["제주시" if lat >= 33.35 else "서귀포시"]
            else:
                sidos = ["기타시도"]
                sigs = ["기타시군"]
                
        routes.at[idx, 'sido'] = ",".join(sidos)
        routes.at[idx, 'sigungu'] = ",".join(sigs)

routes.to_file('routes.geojson', driver='GeoJSON')
print(">> 처리 완료!")
