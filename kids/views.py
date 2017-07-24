# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.contrib.auth.hashers import make_password, check_password
import sendgrid
from keys import SENDGRID_API_KEY,CLARIFAI_API_KEY
from sendgrid.helpers.mail import *
from clarifai.rest import ClarifaiApp

from django.shortcuts import render, redirect,get_list_or_404,get_object_or_404
from forms import SignupForm, LoginForm, PostForm ,LikeForm, CommentForm
import uuid
from models import User, SessionToken, PostModel, LikeModel,CommentModel
from datetime import timedelta
from django.utils import timezone
from recent.settings import BASE_DIR
from textblob import TextBlob
from imgurpython import ImgurClient
import ctypes  # An included library with Python install.


INAPPROPRIATE_WORDS=['arse','arsehole','ass','asshole','badass','bastard','beaver','bitch','bollock','bollocks','boner','bugger','bullshit','bum','cock','crap','creampie','cunt','dick','dickhead','dyke','fag','faggot','fart','fatass',
'fuck','fucked','fucker','fucking','holy shit','jackass','jerk off','kick ass','kick-ass','kike','kikes','nigga','nigger','piss',
'pissed','pizza nigger','shit','shittier','shittiest','shitty','son of a bitch','sons of bitches','STFU','suck','tit','trap','twat','wan']
# Create your views here.

def signup_view(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data.get('name')
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            parentmail = form.cleaned_data.get('parentmail')
            user = User(name=name, username=username, email=email, password=make_password(password),
                        parentmail=parentmail)
            user.save()
            recipient_mail=email
            content_text="Hey "+username+"!! Welcome to the Kids Zone, a social networking site for kids.You have successfully signed up!!"
            sending_mail(recipient_mail,content_text)
            token = SessionToken(user=user)
            token.create_token()
            token.save()
            response = redirect('/feed/')
            response.set_cookie(key='session_token', value=token.session_token)
            return response
    else:
        form = SignupForm()
    return render(request, 'signup.html', {'form': form})


def login_view(request):
    response_data = {}
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = User.objects.filter(username=username).first()
            if user:
                if check_password(password, user.password):
                    token = SessionToken(user=user)
                    token.create_token()
                    token.save()
                    response = redirect('feed/')
                    response.set_cookie(key='session_token', value=token.session_token)
                    return response
                else:
                    response_data['message'] = 'Incorrect Password! Please try again!'

    elif request.method == 'GET':
        form = LoginForm()

    response_data['form'] = form
    return render(request, 'login.html', response_data)


def post_view(request):
    user = check_validation(request)
    if user:
        if request.method == "POST":
            form = PostForm(request.POST, request.FILES)
            if form.is_valid():
                image = form.cleaned_data.get('image')
                caption = form.cleaned_data.get('caption')
                post = PostModel(user=user, image=image, caption=caption)
                post.save()
                path = str(BASE_DIR + post.image.url)
                client = ImgurClient("6fc30e7f6bd87be", "0e21d82e47b11e66d7f6f3874cd269633c25c682")
                post.image_url = client.upload_from_path(path, anon=True)['link']
                post.save()
                app = ClarifaiApp(api_key=CLARIFAI_API_KEY)
                model = app.models.get('nsfw-v1.0')
                response = model.predict_by_url(url=post.image_url)
                concepts_value=response['outputs'][0]['data']['concepts']
                for i in concepts_value:
                    if i['name']=='nsfw':
                        nudity_level=i['value']

                        if nudity_level>=0.85:
                            print response['outputs'][0]['data']['concepts']
                            print nudity_level
                            post.delete()
                            error_message="You are trying to post an inappropriate photo!!"
                            return render(request,"error.html",{'error_message':error_message})
                        else:
                            ctypes.windll.user32.MessageBoxW(0, u"Successfully posted!", u"success", 0)
                            return redirect('/feed/')
        else:
            form = PostForm()

        return render(request, "post.html", {'form': form})
    else:
        return redirect('login')


def posts_of_particular_user(request,user_name):
    posts=PostModel.objects.all().filter(user__username=user_name)
    return render(request,'postsofuser.html',{'posts':posts,'user_name':user_name})


def feed_view(request):
    user=check_validation(request)
    if user:
        posts = PostModel.objects.all().order_by('-created_on')
        for post in posts:
            existing_like = LikeModel.objects.filter(post_id=post.id, user=user).first()
            if existing_like:
                post.has_liked = True
        return render(request, "feed.html", {'posts': posts})
    else:
        return redirect('login')

def logout_view(request):
        cancel_validation(request)
        return redirect('/login/')


def like_view(request):
    user = check_validation(request)
    if user and request.method == 'POST':
        form = LikeForm(request.POST)

        if form.is_valid():
            post_id = form.cleaned_data.get('post').id
            existing_like = LikeModel.objects.filter(post_id=post_id, user=user).first()
            if not existing_like:
                like=LikeModel.objects.create(post_id=post_id,user=user)
                post=PostModel.objects.get(id=post_id)
                content_text=like.user.username + " has just liked your post!"
                recipient_mail=post.user.email
                sending_mail(recipient_mail,content_text)

            else:
                existing_like.delete()

            return redirect('/feed/')
    else:
        return redirect('/login/')

def comment_view(request):
    user = check_validation(request)
    if user and request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            post_id = form.cleaned_data.get('post').id
            comment_text = form.cleaned_data.get('comment_text')
            comment_text_words=TextBlob(comment_text).words
            for word in comment_text_words:
                if word in INAPPROPRIATE_WORDS:
                    error_message="You are trying to add an inapproprite comment!!"
                    return render(request,'error.html',{'error_message':error_message})
                else:
                    comment = CommentModel.objects.create(user=user, post_id=post_id, comment_text=comment_text)
                    comment.save()
                    post=PostModel.objects.get(id=post_id)
                    recipient_mail = post.user.email
                    recipient_name=comment.user.username
                    sending_mail(recipient_mail,content_text=recipient_name+" has commented on your post")
                    return redirect('/feed/')
        else:
            return redirect('/feed/')
    else:
        return redirect('/login/')

def check_validation(request):
    if request.COOKIES.get('session_token'):
        session = SessionToken.objects.filter(session_token=request.COOKIES.get('session_token')).first()
        if session:
            time_to_live = session.created_on + timedelta(days=1)
            if time_to_live > timezone.now():
                return session.user
    else:
        return None
def cancel_validation(request):
    if request.COOKIES.get('session_token'):
        session = SessionToken.objects.filter(session_token=request.COOKIES.get('session_token')).first()
        if session:
            session.delete()
        else:
            pass


def sending_mail(recipient_mail,content_text):
    sg = sendgrid.SendGridAPIClient(apikey=SENDGRID_API_KEY)
    from_email = Email("kidssphere@gmail.com")
    to_email = Email(recipient_mail)
    subject = "Notification from Kids Zone, a social networking site for kids!!"
    content = Content("text/plain", content_text)
    mail = Mail(from_email, subject, to_email, content)
    response = sg.client.mail.send.post(request_body=mail.get())
