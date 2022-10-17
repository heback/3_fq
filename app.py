import random
from datetime import datetime

import streamlit as st
import sqlite3
import re
import pandas as pd
import numpy as np
from plotly import graph_objs as go

# 한글 정규표현식 패턴
hangul = '^[가-힣]{2,5}$'

# 문항 카테고리
question_category = ['가족애', '우애', '동료애']

# 데이터베이스 연결
con = sqlite3.connect('db.db')
cur = con.cursor()


# 사용자 정보 저장
def save_user(**val):
    cur.execute(f"INSERT INTO users "
                f"(user_name, user_pw, user_birth, user_gender, user_type) "
                f"VALUES ("
                f"'{val['user_name']}',"
                f"'{val['user_pw']}',"
                f"'{val['user_birth']}',"
                f"'{val['user_gender']}',"
                f"'{val['user_type']}')")
    con.commit()
    return cur.lastrowid


def user_info(user_id):
    cur.execute(f"SELECT * FROM users WHERE user_id='{user_id}'")
    row = cur.fetchone()
    st.info(f"아이디: {row[0]}, 성명: {row[1]}({row[4]})")


def user_login(user_id):
    cur.execute(f"SELECT * FROM users WHERE user_id='{user_id}'")
    row = cur.fetchone()
    return row

def user_check(user_id):
    cur.execute(f"SELECT COUNT(*) FROM users WHERE user_id='{user_id}'")
    row = cur.fetchone()
    return row[0]

# 응답 확인
def response_initialize(user_id):
    cur.execute(f"SELECT COUNT(*) FROM responses WHERE user_id='{user_id}'")
    row = cur.fetchone()
    if not row[0]:
        for i in range(0, 150):
            cate = i // 50
            cur.execute(f"INSERT INTO responses (user_id, question_no, question_category, response) VALUES "
                        f"('{user_id}', {i+1}, {cate}, 0)")
            con.commit()


# 응답 추가
def add_response(*args):
    response = 0 if args[1] else 1
    sql = f"UPDATE responses SET response={response} WHERE id={args[0]}"
    # print(sql)
    cur.execute(sql)
    con.commit()


# 문항 섞기
def shuffle_questions(user_id):
    cur.execute(f"SELECT COUNT(*) FROM randnos WHERE userid='{user_id}'")
    res = cur.fetchone()
    cnt = res[0]

    if cnt == 0:
        cur.execute(f"INSERT INTO randnos (randno, userid) "
                    f"SELECT no, {user_id} FROM questions "
                    f"ORDER BY random()")
        con.commit()


st.header('3-FQ 판별 프로그램 참여')
st.info('중·고등 학생의 경우, 같은반 학생은 \'친구\', 다른 학년 혹은 학반 학생은 \'동료\'로 생각하고 문항에 응답해 주세요.')

tab1, tab2, tab3 = st.tabs(['참가자 등록', '참여', '결과 조회'])

with tab1:
    st.subheader('참가자 등록')

    with st.form('users', clear_on_submit=True):
        user_name = st.text_input('성명', max_chars=5)
        user_pw = st.text_input('비밀번호', type='password', max_chars=4)
        user_birth = st.date_input('생년월일', min_value=datetime.strptime('1930-01-01','%Y-%m-%d'),
                                   max_value=datetime.strptime('2022-12-31','%Y-%m-%d'))
        user_gender = st.radio('성별', options=['남', '여'], horizontal=True, index=0)
        user_type = st.radio('구분', options=['중', '고', '성인'], horizontal=True, index=0)
        submitted = st.form_submit_button('등록')

        if submitted:

            # name 확인
            if len(user_name) < 2:
                st.warning('성명이 적절한지 확인하세요.')
                st.stop()

            if not re.match(hangul, user_name):
                st.warning('성명은 한글만 입력합니다.')
                st.stop()

            user_id = save_user(user_name=user_name,
                                user_pw=user_pw,
                                user_birth=user_birth,
                                user_gender=user_gender,
                                user_type=user_type)
            st.session_state['user_id'] = user_id
            st.info(f'사용자 정보를 저장하였습니다. 참여 아이디는 {user_id} 입니다. 결과 확인을 위해 필요하기 때문에 꼭 기억하셔야 합니다. 참여 탭을 클릭하여 시작하세요.')

with tab2:
    st.subheader('참여')

    if 'user_id' not in st.session_state.keys():
        st.warning('참가자 등록을 먼저 하여야 합니다.')

    else:

        user_info(st.session_state['user_id'])

        # 응답 초기화(최초 한 번만 적용됨)
        response_initialize(st.session_state['user_id'])

        # 응답 정보 불러오기
        cur.execute(f"SELECT * FROM responses WHERE user_id='{st.session_state['user_id']}'")
        res = cur.fetchall()
        # print(res)
        # res[0][0] : id
        # res[0][1] : user_id
        # res[0][2] : question_no
        # res[0][3] : question_category
        # res[0][4] : response

        st.info('모든 페이지(1~15 페이지)의 문항(150문항)에 대해 자신에게 해당하는 것을 선택(체크)하세요.')

        # 페이지 설정
        pages = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]
        if 'page' not in st.session_state.keys():
            st.session_state['page'] = 1

        st.markdown(f"### {st.session_state['page']} 페이지")

        # 문항 랜덤하게 썪기
        shuffle_questions(st.session_state['user_id'])

        # 문항 불러오기
        cur.execute(f"SELECT r.randno, q.category, q.q_no, q.question, r.no "
                    f"FROM questions as q, randnos as r "
                    f"WHERE q.no = r.randno AND r.userid = {st.session_state['user_id']} "
                    f"ORDER BY r.no ASC LIMIT 10 OFFSET {(st.session_state['page'] - 1)*10}")
        rows = cur.fetchall()
        # print(rows)

        # 헤더
        col1, col2 = st.columns([8, 1])
        with col1:
            st.write('문항')
        with col2:
            st.write('예')

        # 문항 출력
        for row in rows:

            col1, col2 = st.columns([8, 1])
            with col1:
                st.write(row[3])
                # st.write(row[0])
                # st.write(res[row[0]-1][0])
            with col2:
                st.checkbox('', key=row[0], value=res[row[0]-1][4], on_change=add_response,
                                args=(res[row[0]-1][0], res[row[0]-1][4]))

        col1, col2, col3 = st.columns([1, 6, 1])
        with col1:
            if st.session_state['page'] != 1:
                prev = st.button('이전')
                if prev:
                    st.session_state['page'] -= 1
                    st.experimental_rerun()

        with col3:
            if st.session_state['page'] != 15:
                nex = st.button('다음')
                if nex:
                    st.session_state['page'] += 1
                    st.experimental_rerun()

        col1, col2, col3 = st.columns([3, 1, 6])
        with col1:
            page = st.number_input('페이지', min_value=1, max_value=15)
        with col2:
            mv_btn = st.button('이동')
            if mv_btn:
                st.session_state['page'] = page
                st.experimental_rerun()

with tab3:
    # print('결과 조회')
    st.subheader('결과 조회')

    if 'user_id' not in st.session_state.keys():
        st.info('참여 완료한 후 혹은 로그인 후 결과를 조회하세요.')

        with st.form('login', clear_on_submit=True):
            col1, col2, col3, col4 = st.columns([2, 3, 3, 2])
            with col1:
                user_id = st.text_input('아이디(숫자)')
            with col2:
                user_name = st.text_input('성명')
            with col3:
                user_pw = st.text_input('비밀번호', type='password')
            with col4:
                sumit_btn = st.form_submit_button('로그인')


                if sumit_btn:
                    if len(user_id) < 1:
                        st.warning('아이디를 확인하세요.')
                        st.stop()

                    if len(user_name) < 2:
                        st.warning('성명을 확인하세요.')
                        st.stop()

                    if len(user_pw) < 4:
                        st.warning('비밀번호를 확인하세요.')
                        st.stop()

                    # 아이디 확인
                    if not user_check(user_id):
                        st.warning('존재하지 않는 아이디입니다.')
                        st.stop()

                    row = user_login(user_id)
                    if user_name != row[1]:
                        st.warning('성명이 일치하지 않습니다.')
                        st.stop()
                    if user_pw != row[2]:
                        st.warning('비밀번호가 일치하지 않습니다.')
                        st.stop()

                    st.session_state['user_id'] = user_id
                    st.experimental_rerun()

    if 'user_id' in st.session_state.keys():

        # 전체 평균(구분별)
        sql1 = f"SELECT question_category, sum(response) FROM responses GROUP BY question_category"
        cur.execute(sql1)
        res1 = cur.fetchall()
        # print(res1)

        if res1[0][1] > 0:

            # 사용자 평균(구분별)
            sql2 = f"SELECT question_category, sum(response) FROM responses WHERE user_id='{st.session_state['user_id']}' GROUP BY question_category"
            cur.execute(sql2)
            res2 = cur.fetchall()
            # print(res2)

            categories = ['Familyship', 'Friendship', 'Fellowship']
            index = ['평균', '본인']
            data = [[res1[0][1], res1[1][1], res1[2][1]],
                [np.around(res2[0][1]*100/res1[0][1], 1),
                 np.around(res2[1][1]*100/res1[1][1], 1),
                 np.around(res2[2][1]*100/res1[2][1], 1)]]
            df = pd.DataFrame(data, index=index, columns=categories)

            st.dataframe(df.style.format(subset=categories, formatter="{:.1f}"))

            fig = go.Figure()

            fig.add_trace(go.Scatterpolar(
                r=data[0],
                theta=categories,
                fill='toself',
                name='평균'
            ))
            fig.add_trace(go.Scatterpolar(
                r=data[1],
                theta=categories,
                fill='toself',
                name='본인'
            ))

            fig.update_layout(
                polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 200]
                )),
                showlegend=True
            )
            st.subheader('친화성 다이어그램')
            st.write(fig)

        logout_btn = st.button('로그아웃')
        if logout_btn:
            del st.session_state['user_id']
            st.experimental_rerun()


hide_streamlit_style = """
	<style>
	/* This is to hide hamburger menu completely */
	#MainMenu {visibility: hidden;}
	/* This is to hide Streamlit footer */
	footer {visibility: hidden;}
	/*
	If you did not hide the hamburger menu completely,
	you can use the following styles to control which items on the menu to hide.
	*/
	ul[data-testid=main-menu-list] > li:nth-of-type(4), /* Documentation */
	ul[data-testid=main-menu-list] > li:nth-of-type(5), /* Ask a question */
	ul[data-testid=main-menu-list] > li:nth-of-type(6), /* Report a bug */
	ul[data-testid=main-menu-list] > li:nth-of-type(7), /* Streamlit for Teams */
	ul[data-testid=main-menu-list] > div:nth-of-type(2) /* 2nd divider */
		{display: none;}
	</style>
"""

st.markdown(hide_streamlit_style, unsafe_allow_html=True)
