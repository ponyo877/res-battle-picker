import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('YOUTUBE_API_KEY')
reply_count_threshold = 2

def main():
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    try:
        request = youtube.search().list(
            part='snippet',
            type='video',
            channelId='UCSD8-ScYTwb2AxgmQfMHIAQ',  # @tamurakae2
            maxResults=1,
        )
        response = request.execute()
        for item in response.get('items', []):
            video_id = item['id']['videoId']
            next_page_token = None
            cnt = 0
            while True:
                request = youtube.commentThreads().list(
                    part='snippet,replies',
                    videoId=video_id,
                    maxResults=150,
                    pageToken=next_page_token,
                    textFormat='plainText',
                    order='relevance'
                )
                response = request.execute()
                for comment_thread in response.get('items', []):
                    snippet = comment_thread['snippet']
                    top_comment = snippet['topLevelComment']['snippet']['textDisplay']
                    reply_count = snippet['totalReplyCount']
                    like_count = snippet['topLevelComment']['snippet']['likeCount']
                    like_count_list = [like_count]
                    if reply_count > reply_count_threshold:
                        cnt += 1
                        for reply in comment_thread['replies']['comments']:
                            reply_text = reply['snippet']['textDisplay']
                            reply_like_count = reply['snippet']['likeCount']
                            like_count_list.append(reply_like_count)
                            print(f"  Reply: {reply_text} Likes: {reply_like_count}")
                        print(f"Comment {cnt} (Replies: {reply_count}): {top_comment} Likes: {like_count_list}")
                    # if reply_count > 5:
                    #     reply_page_token = None
                    #     while True:
                    #         reply_request = youtube.comments().list(
                    #             part='snippet',
                    #             parentId=snippet['topLevelComment']['id'],
                    #             maxResults=100,
                    #             pageToken=reply_page_token,
                    #         )
                    #         reply_response = reply_request.execute()

                    #         for reply in reply_response.get('items', []):
                    #             reply_text = reply['snippet']['textDisplay']
                    #             reply_like_count = reply['snippet']['likeCount']
                    #             print(f"    Reply: {reply_text} Likes: {reply_like_count}")

                    #         reply_page_token = reply_response.get('nextPageToken')
                    #         if not reply_page_token:
                    #             break
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
    except HttpError as e:
        print(f'An HTTP error {e.resp.status} occurred: {e.content}')


if __name__ == "__main__":
    main()
