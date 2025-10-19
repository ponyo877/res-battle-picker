import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from transformers import pipeline, BertJapaneseTokenizer, AutoModelForSequenceClassification

load_dotenv()
API_KEY = os.getenv('YOUTUBE_API_KEY')
reply_count_threshold = 5

tokenizer = BertJapaneseTokenizer.from_pretrained(
    "christian-phu/bert-finetuned-japanese-sentiment",
    mecab_kwargs={"mecab_dic": "unidic"},
    model_max_length=512
)
model = AutoModelForSequenceClassification.from_pretrained("christian-phu/bert-finetuned-japanese-sentiment")
classifier = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer, truncation=True, max_length=512)

def is_negative(comment):
    results = classifier(comment, top_k=None, truncation=True, max_length=512)
    for result in results:
        if result['label'] == 'positive' and result['score'] < 0.5:
            return True
    return False

def get_videos(youtube, channel_id, page_token=None):
    request = youtube.search().list(
        part='snippet',
        type='video',
        channelId=channel_id,
        maxResults=100,
        pageToken=page_token,
    )
    response = request.execute()
    return response.get('items', []), response.get('nextPageToken')

def get_comment_threads(youtube, video_id, page_token=None):
    request = youtube.commentThreads().list(
        part='snippet,replies',
        videoId=video_id,
        maxResults=100,
        pageToken=page_token,
        textFormat='plainText',
        order='relevance'
    )
    response = request.execute()
    return response.get('items', []), response.get('nextPageToken')

def get_replies(youtube, parent_id, page_token=None):
    request = youtube.comments().list(
        part='snippet',
        parentId=parent_id,
        maxResults=100,
        pageToken=page_token,
        textFormat='plainText',
    )
    response = request.execute()
    return response.get('items', []), response.get('nextPageToken')

def is_negative_threads(reply_items):
    like_count_sum = 0
    negative_cnt = 0
    if len(reply_items) == 0:
        return False
    for reply in reply_items:
        reply_snippet = reply['snippet']
        reply_text = reply_snippet['textDisplay']
        reply_like_count = reply_snippet['likeCount']
        like_count_sum += reply_like_count
        if is_negative(reply_text):
            negative_cnt += 1
    return negative_cnt / len(reply_items) > 0.5

def is_better_res_battle(top_comment_snippet, reply_items):
    top_comment_like_count = top_comment_snippet['likeCount']
    for reply in reply_items:
        reply_snippet = reply['snippet']
        reply_like_count = reply_snippet['likeCount']
        if reply_like_count > top_comment_like_count and reply_snippet['authorChannelId']['value'] != top_comment_snippet['authorChannelId']['value']:
            return True
    return False


def main():
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    better_res_battles = []
    cnt = 0
    videos_token = None
    try:
        while True:
            video_items, videos_token = get_videos(youtube, 'UCSD8-ScYTwb2AxgmQfMHIAQ', videos_token)
            for item in video_items:
                cnt += 1
                video_id = item['id']['videoId']
                comment_threads_token = None
                print(f'Count {cnt}: Processing video ID: {video_id}')
                while True:
                    comment_thread_items, comment_threads_token = get_comment_threads(youtube, video_id, comment_threads_token)
                    for comment_thread in comment_thread_items:
                        snippet = comment_thread['snippet']
                        top_comment_snippet = snippet['topLevelComment']['snippet']
                        top_comment_id = snippet['topLevelComment']['id']
                        reply_count = snippet['totalReplyCount']
                        if reply_count < reply_count_threshold:
                            continue
                        all_reply_items = []
                        replys_token = None
                        while True:
                            reply_items, replys_token = get_replies(youtube, top_comment_id, replys_token)
                            all_reply_items.extend(reply_items)
                            if not replys_token:
                                break
                        if not is_negative_threads(all_reply_items):
                            continue
                        if not is_better_res_battle(top_comment_snippet, all_reply_items):
                            continue
                        better_res_battles.append({
                            'video_id': video_id,
                            'top_comment': top_comment_snippet['textDisplay'],
                            'top_comment_like_count': top_comment_snippet['likeCount'],
                            'reply_count': reply_count,
                        })
                    if not comment_threads_token:
                        break
            if not videos_token:
                break
        for battle in better_res_battles:
            print(f"Video ID: {battle['video_id']}")
            print(f"Top Comment: {battle['top_comment']}")
            print(f"Top Comment Like Count: {battle['top_comment_like_count']}")
            print(f"Reply Count: {battle['reply_count']}")
            print("-----")
    except HttpError as e:
        print(f'An HTTP error {e.resp.status} occurred: {e.content}')


if __name__ == "__main__":
    main()
