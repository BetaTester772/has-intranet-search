import datetime
import time
from io import BytesIO

import numpy as np
import pandas as pd
from fastapi import FastAPI, Depends, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from openai import OpenAI
from pydantic import BaseModel
import jwt

# get config from .env file
from starlette.config import Config

env = Config('.env')
openai_api_key = env.get('OPENAI_API_KEY')
SECRET_KEY = env.get('SECRET_KEY')

client = OpenAI(api_key=openai_api_key)

from sklearn.metrics.pairwise import cosine_similarity

from transformers import AutoModel, AutoTokenizer, pipeline

model = AutoModel.from_pretrained("yjgwak/klue-bert-base-finetuned-squard-kor-v1")
tokenizer = AutoTokenizer.from_pretrained("yjgwak/klue-bert-base-finetuned-squard-kor-v1")
qa_pipe = pipeline("question-answering", model="yjgwak/klue-bert-base-finetuned-squad-kor-v1")

from konlpy.tag import Okt

okt = Okt()


def load_df_for_search(path):
    df = pd.read_csv(path)
    df.drop_duplicates(subset=['title', 'content_text'], keep='first', inplace=True)
    df.fillna('', inplace=True)
    df['ada_embedding'] = df.ada_embedding.apply(eval).apply(np.array)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date', ascending=False)
    df.reset_index(drop=True, inplace=True)
    # date cut
    df = df[df['date'] >= '2020-01-01']
    # print(df)
    return df


def search_post(df, context, n=3, pprint=False):
    # print("Embedding start")
    embedding = get_embedding(context, model='text-embedding-3-small')
    # print("Embedding end")
    df['similarities'] = df.ada_embedding.apply(
            lambda x: cosine_similarity(np.array(x).reshape(1, -1), np.array(embedding).reshape(1, -1)))
    res = df.sort_values('similarities', ascending=False).head(n)
    if pprint:
        for idx, row in res.iterrows():
            print(row['title'])
            # print(row['content_text'])
            # print(row['content_images'])
            print(row['similarities'])
            print()
    return res


def get_embedding(text, model="text-embedding-3-small"):
    text = text.replace("\n", " ")
    return client.embeddings.create(input=[text], model=model).data[0].embedding


def get_keyword_from_pd_row(row: pd.DataFrame) -> list:
    result = []
    # print(row['combined'])
    # print("=" * 50)

    try:
        keywords = summarize_with_keywords([split_words(row['combined'])], min_count=2)
    except:
        # print(row['title'])
        keywords = summarize_with_keywords([split_words(row['combined'])], min_count=1)
    for word, r in keywords.items():
        result.append(word)
        if len(result) > 5:
            break

    if row['title'].startswith('['):
        sub_title = row['title'].split(']', 1)[0][1:].strip()
        result.append(sub_title)

    if row['writer']:
        result.append(row['writer'])

    return result


def find_word_from_df_keyword(df: pd.DataFrame, word: str, n=10, pprint=False):
    i_list = []
    for i in range(len(df)):
        if word in df.iloc[i]['keywords'] or word in df.iloc[i]['title'] or word in df.iloc[i]['writer']:
            i_list.append(i)

        if len(i_list) > n:
            break

    result = df.iloc[i_list]

    if pprint:
        for idx, row in result.iterrows():
            print(row['title'])
            print(row['keywords'])
            print()

    return result


def split_text_with_okt(text: str, pprint=False):
    result = okt.nouns(text)
    for i in range(len(result)):
        if result[i].endswith('대학교'):
            result.append(result[i][:-2])
    if pprint:
        print(text, "->", result)
    return result


def find_all_include_word(df, q: str):
    i_list = []
    for i in range(len(df)):
        if q in df.iloc[i]['combined']:
            i_list.append(i)

    result = df.iloc[i_list]

    return result


from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter
from konlpy.tag import Okt

okt = Okt()


def load_stopwords(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        stopwords = [line.strip() for line in f.readlines()]
    return stopwords


def split_noun_sentences(text):
    nouns = okt.nouns(text)
    return ' '.join(nouns)


def filter_stopwords(words, stopwords):
    return [word for word in words if word not in stopwords]


stopword_file = 'stopword.txt'
stopwords = load_stopwords(stopword_file)
font_path = 'NanumGothicCoding.ttf'


def create_word_cloud(text):
    nouns_text = split_noun_sentences(text)
    nouns_list = nouns_text.split()

    filtered_nouns = filter_stopwords(nouns_list, stopwords)
    filtered_text = ' '.join(filtered_nouns)

    word_counts = Counter(filtered_text.split())

    important_words = dict(word_counts.most_common(20))

    # print(important_words)

    wordcloud = WordCloud(font_path=font_path, width=800, height=400,
                          background_color='white').generate_from_frequencies(important_words)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    return fig


database = load_df_for_search('embedded_df_with_keywords.csv')

app = FastAPI()

app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
)


# response model
class search_response(BaseModel):
    time: float
    count: int
    result: list
    q: list


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="https://ssoapi.betatester772.dev/api/v1/auth/token")


def verify_token(token: str = Depends(oauth2_scheme)):
    # print(SECRET_KEY)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


board_list = database['board_name'].unique().tolist()

@app.get("/board")
def get_board_list(_=Depends(verify_token)) -> dict[str, list[str]]:
    return {"result": board_list}

return_columns = ['board_name', 'title', 'writer', 'date', 'content_text', 'content_images', 'link']

@app.get("/search/1", response_model=search_response)
def keyword_search(q: str,
                   start_date: datetime.datetime = datetime.datetime.now().date() - datetime.timedelta(days=365),
                   end_date: datetime.datetime = datetime.datetime.now().date(),
                   board: str | None = None,
                   _=Depends(verify_token)):
    if board is None:
        board = board_list
    else:
        string = board.strip('[]').split(',')
        board = [s.strip() for s in string]
    print(board)
    if not start_date:
        start_date = datetime.datetime.now().date() - datetime.timedelta(days=365)
    if not end_date:
        end_date = datetime.datetime.now().date()
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    df = database[(database['board_name'].apply(lambda x: x in board)) & (database['date'] >= start_date) & (
                database['date'] <= end_date)]

    start_time = time.time()
    q_list = split_text_with_okt(q)
    result = []
    for q in q_list:
        data = find_word_from_df_keyword(df, q)
        for i, content in data[return_columns].to_dict(
                orient='index').items():
            # print(content['content_text'])
            data_dict = {}
            data_dict['idx'] = i
            for k, v in content.items():
                data_dict[k] = v
            result.append(data_dict)
    return {
            "time"  : time.time() - start_time,
            "count" : len(result),
            "result": result,
            "q"     : q_list
    }


@app.get("/search/2", response_model=search_response)
def embedding_search(q: str,
                     start_date: datetime.datetime = datetime.datetime.now().date() - datetime.timedelta(days=365),
                     end_date: datetime.datetime = datetime.datetime.now().date(),
                     board: str | None = None,
                     _=Depends(verify_token)):
    # print("q:", q)
    if board is None:
        board = board_list
    else:
        string = board.strip('[]').split(',')
        board = [s.strip() for s in string]
    print(board)
    if not start_date:
        start_date = datetime.datetime.now().date() - datetime.timedelta(days=365)
    if not end_date:
        end_date = datetime.datetime.now().date()
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    df = database[(database['board_name'].apply(lambda x: x in board)) & (database['date'] >= start_date) & (
            database['date'] <= end_date)]

    q_list = split_text_with_okt(q)

    start_time = time.time()
    data = search_post(df, q, n=3, pprint=False)
    result = []
    for i, content in data[return_columns].to_dict(
            orient='index').items():
        data_dict = {}
        data_dict['idx'] = i
        for k, v in content.items():
            data_dict[k] = v
        result.append(data_dict)
    return {
            "time"  : time.time() - start_time,
            "count" : len(result),
            "result": result,
            "q"     : q_list
    }


@app.get("/search/3", response_model=search_response)
def full_search(q: str,
                start_date: datetime.datetime = datetime.datetime.now().date() - datetime.timedelta(days=365),
                end_date: datetime.datetime = datetime.datetime.now().date(),
                board: str | None = None,
                _=Depends(verify_token)):
    if board is None:
        board = board_list
    else:
        string = board.strip('[]').split(',')
        board = [s.strip() for s in string]
    print(board)
    if not start_date:
        start_date = datetime.datetime.now().date() - datetime.timedelta(days=365)
    if not end_date:
        end_date = datetime.datetime.now().date()
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    df = database[(database['board_name'].apply(lambda x: x in board)) & (database['date'] >= start_date) & (
            database['date'] <= end_date)]

    start_time = time.time()
    q_list = split_text_with_okt(q)
    result = []
    for q in q_list:
        data = find_all_include_word(df, q)
        # raise ValueError(data[['title', 'writer', 'content_text', 'content_images']].to_dict(orient='index'))
        for i, content in data[return_columns].to_dict(
                orient='index').items():
            data_dict = {}
            data_dict['idx'] = i
            for k, v in content.items():
                data_dict[k] = v
            result.append(data_dict)

    return {
            "time"  : time.time() - start_time,
            "count" : len(result),
            "result": result,
            "q"     : q_list
    }


@app.get("/wordcloud")
def wordcloud(idx: int):
    text = database.iloc[idx]['combined']
    fig = create_word_cloud(text)
    buf = BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@app.get("/qa", response_model=search_response)
def qa(q: str,
                start_date: datetime.datetime = datetime.datetime.now().date() - datetime.timedelta(days=365),
                end_date: datetime.datetime = datetime.datetime.now().date(),
                board: str | None = None,
                _=Depends(verify_token)):
    start_time = time.time()
    if not q.endswith("?"):
        raise HTTPException(status_code=400, detail="Question should end with '?'")
    search_result_list = embedding_search(q=q[:-1], start_date=start_date, end_date=end_date, board=board)['result'][:10]
    search_result_list = sorted(search_result_list, key=lambda x: x['date'], reverse=True)
    # print(search_result_list)
    done = False
    q_list = split_text_with_okt(q[:-1])
    for search_result in search_result_list:
        done = True
        combined_content = search_result['title'] + search_result['content_text'] + search_result['content_images']
        # print(search_result['date'])
        combined_content_tokens = split_text_with_okt(combined_content)
        # print(combined_content_tokens)
        for q_token in q_list[:-1]:
            # print(q_token)
            if q_token not in combined_content_tokens:
                done = False
                break
        if done:
            # print("complete", search_result['title'])
            break
        # print()
        # return {"error": "Question does not contain all token in the context."}
    if done:
        # print(combined_content)
        qa_result = qa_pipe(question=q, context=combined_content)

        # print(qa_result['score'])

        if qa_result['score'] < 0.01:
            return {
                    "count" : 0,
                    "time"  : time.time() - start_time,
                    "result": [],
                    "q"     : q_list
            }

        result = {}

        result['question'] = q
        result['context'] = search_result

        for k, v in qa_result.items():
            result[k] = v

        return {
                "count" : 1,
                "time"  : time.time() - start_time,
                "result": [result],
                "q"     : q_list

        }
    else:
        return {
                "count" : 0,
                "time"  : time.time() - start_time,
                "result": [],
                "q"     : q_list
        }
