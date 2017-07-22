# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.contrib.auth.hashers import make_password, check_password
import sendgrid
from keys import SENDGRID_API_KEY
from sendgrid.helpers.mail import *
from clarifai.rest import ClarifaiApp

from django.shortcuts import render, redirect,get_list_or_404,get_object_or_404
from forms import SignupForm, LoginForm, PostForm ,CommentForm
import uuid
from models import User, SessionToken, PostModel ,LikeModel,CommentModel
from datetime import timedelta
from django.utils import timezone
from recent.settings import BASE_DIR
from imgurpython import ImgurClient
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
                app = ClarifaiApp(api_key="a73ee15ab37446a897cdcbbce2286bf9")
                model = app.models.get('nsfw-v1.0')
                response = model.predict_by_url(url=post.image_url)
                nudity_level=response['outputs'][0]['data']['concepts'][0]['value']
                if nudity_level>=0.85:
                    error_message="You are trying to post an inappropriate photo!!"
                    post.delete()
                    return render(request,"error.html",{'error_message':error_message})
                else:
                    return redirect('/feed/')
        else:
            form = PostForm()

        return render(request, "post.html", {'form': form})
    else:
        return redirect('login')


def feed_view(request):
    if check_validation(request):
        posts = PostModel.objects.all().order_by('-created_on')
        return render(request, "feed.html", {'posts': posts})
    else:
        return redirect('login')

def logout_view(request):
        cancel_validation(request)
        return redirect('/login/')

#
# def like_view(request):
#     user=check_validation(request)
#     if user:
#         form = LikeForm(request.POST)
#         post_id=form.cleaned_data.get('post').id
#         existing_like=LikeModel.objects.all().filter(user=user,post_id=post_id).first()
#         if existing_like:
#
#             existing_like.delete()
#         else:
#             LikeModel.create(user=user,post_id=post_id)
#     else:
#         form=LoginForm()
#     return  render(request,'feed.html',{'form':form })

def comment_view(request):
    user = check_validation(request)
    if user and request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            username_of_post=form.cleaned_data.get('post')
            post_id = form.cleaned_data.get('post').id
            print post_id
            comment_text = form.cleaned_data.get('comment_text')
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
