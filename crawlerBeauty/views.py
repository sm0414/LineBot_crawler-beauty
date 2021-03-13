from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextSendMessage, TemplateSendMessage, ImageCarouselTemplate, ImageCarouselColumn, PostbackTemplateAction

import requests
from bs4 import BeautifulSoup

from .models import CrawlerBeauty

line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)


@csrf_exempt
def callback(request):
    if request.method == 'POST':
        signature = request.META['HTTP_X_LINE_SIGNATURE']
        body = request.body.decode('utf-8')

        try:
            events = parser.parse(body, signature)  # 傳入的事件
        except InvalidSignatureError:
            return HttpResponseForbidden()
        except LineBotApiError:
            return HttpResponseBadRequest()

        for event in events:
            if isinstance(event, MessageEvent):  # 如果有訊息事件
                text = event.message.text
                result = ''

                cb = CrawlerBeauty.objects.filter(id=1)
                if cb.count() > 0:
                    nowPage = cb[0].page
                    result = cb[0].result

                if '表特' in text:
                    response = getBeauty(0, 'not keyword')

                    line_bot_api.reply_message(  # 回復傳入的訊息文字
                        event.reply_token,
                        TextSendMessage(response)
                    )
                elif '下' in text:
                    response = getBeauty(nowPage-1, 'not keyword')

                    line_bot_api.reply_message(  # 回復傳入的訊息文字
                        event.reply_token,
                        TextSendMessage(response)
                    )
                elif '上' in text:
                    response = getBeauty(nowPage+1, 'not keyword')

                    line_bot_api.reply_message(  # 回復傳入的訊息文字
                        event.reply_token,
                        TextSendMessage(response)
                    )
                elif text in result and len(text) >= 2:
                    imageCarousel = getBeauty(nowPage, text)

                    line_bot_api.reply_message(  # 回復傳入的訊息文字
                        event.reply_token,
                        imageCarousel
                    )
                else:
                    line_bot_api.reply_message(  # 回復傳入的訊息文字
                        event.reply_token,
                        TextSendMessage(text)
                    )
        return HttpResponse()
    else:
        return HttpResponseBadRequest()

def getBeauty(page, keyword):
    if page:
        url = 'https://www.ptt.cc/bbs/Beauty/index%d.html' % page
    else:
        url = 'https://www.ptt.cc/bbs/Beauty/index.html'

    response = requests.get(url,
                            headers={'Cookie': 'over18=1;'}
                            ).text
    soup = BeautifulSoup(response, 'html.parser')

    try:
        previousPage = soup.find_all('a', class_='btn wide')[1].get('href')
    except:
        return '前面沒東西了!! Σ(*ﾟдﾟﾉ)ﾉ'

    nowPage = int(previousPage.lstrip('/bbs/Beauty/index').rstrip('.html'))+1

    titleWithUrl = soup.select('div .title')

    result = ''
    statusUrl = 0
    for row in titleWithUrl:
        if row.find('a') is not None and ('正妹' in row.find('a').text or '帥哥' in row.find('a').text):
            title = row.find('a').text
            articleUrl = 'https://www.ptt.cc' + row.find('a').get('href')

            if keyword in title:
                statusUrl = articleUrl

            result += title + '\n' + articleUrl + '\n'


    # 更新頁面結果及頁數
    updateCrawlerBeauty(nowPage, result)

    if statusUrl:
        articleResponse = requests.get(statusUrl,
                                headers={'Cookie': 'over18=1;'}
                                ).text
        articleSoup = BeautifulSoup(articleResponse, 'html.parser')
        images = articleSoup.select('a[rel="nofollow"]')
        columns = imageCarouselColumn(images)

        imageCarousel = TemplateSendMessage(
            alt_text='目錄 template',
            template=ImageCarouselTemplate(
                columns=columns
            )
        )

        return imageCarousel

    return str(page)+'/'+str(nowPage)+result

def imageCarouselColumn(images):
    columns = []

    for idx, image in enumerate(images):
        columns.append(
            ImageCarouselColumn(
                image_url=image.get('href'),
                action=PostbackTemplateAction(
                    label='圖%s' % str(idx+1),
                    text=image.get('href'),
                    data='action=buy&itemid=%s' % str(idx+1)
                )
            )
        )

        if idx == 9:
            break

    return columns

def updateCrawlerBeauty(nowPage, result):
    cb = CrawlerBeauty.objects.filter(id=1)
    if cb.count() == 0:
        CrawlerBeauty.objects.create(page=nowPage, result=result).save()
    else:
        cb.update(page=nowPage, result=result)
