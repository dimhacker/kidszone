# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.contrib.auth.hashers import make_password, check_password
import sendgrid
from keys import SENDGRID_API_KEY,CLARIFAI_API_KEY #Clarifai api stores the image uploaded by the user on cloud and provides us the url of image
from sendgrid.helpers.mail import *                    #sendgrid api helps in sending mail to the provided email id
from clarifai.rest import ClarifaiApp
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect,Http404
from forms import SignupForm, LoginForm, PostForm ,LikeForm, CommentForm,CommentLikeForm,StatusForm,ProfileForm
from models import User, SessionToken, PostModel, LikeModel,CommentModel,CommentLikeModel
from datetime import timedelta
from django.utils import timezone
from recent.settings import BASE_DIR
from textblob import TextBlob           #Textblob is used for text processing
from imgurpython import ImgurClient
from django.core.paginator import Paginator,PageNotAnInteger,EmptyPage
from paralleldots import abuse

import ctypes  # An included library with Python install.


INAPPROPRIATE_WORDS=['arse','arsehole','ass','asshole','badass','bastard','beaver','bitch','bollock','bollocks','boner','bugger','bullshit','bum','cock','crap','creampie','cunt','dick','dickhead','dyke','fag','faggot','fart','fatass',
'fuck','fucked','fucker','fucking','holy shit','jackass','jerk off','kick ass','kick-ass','kike','kikes','nigga','nigger','piss',
'pissed','pizza nigger','shit','shittier','shittiest','shitty','son of a bitch','sons of bitches','STFU','suck','tit','trap','twat','wan']
# Create your views here.

def signup_view(request):               #view for signup.html and all other invalid urls
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data.get('name')
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            parentmail = form.cleaned_data.get('parentmail')
            user = User(name=name, username=username, email=email, password=make_password(password),parentmail=parentmail)  #make_password converts a string into hashcode with is one way encryption
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


def login_view(request):                    #view for login.html
    response_data = {}
    if request.method == "POST":
        form = LoginForm(request.POST)
        for field in form:
            print field.errors

        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = User.objects.filter(username=username).first()
            if user:
                if check_password(password, user.password):
                    token = SessionToken(user=user)      #generating session for logged in user
                    token.create_token()
                    token.save()
                    response = redirect('/feed/')
                    response.set_cookie(key='session_token', value=token.session_token)   #storing generated session as cookie
                    return response
                else:
                    response_data['message'] = 'Incorrect Password! Please try again!'
            else:
                response_data['message']="Invalid User! Please try again!"
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
                client = ImgurClient("cf01c350e85ac5e", "242c1c9414317fa82779c081c50bdffcac64a6ee")
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
                            return redirect('/feed/')
        else:
            form = PostForm()

        return render(request, "post.html", {'form': form})
    else:
        return redirect('login')


def posts_of_particular_user(request,user_name):    #view displaying the posts by a particular user
    USER=check_validation(request)
    if USER:
        user=User.objects.all().filter(username=user_name).first()
        if user:
                posts = PostModel.objects.all().filter(user__username=user_name)
                return render(request, 'feed.html', {'posts': posts} )
        else:
            raise Http404

    else:
        return  redirect('/login/')

def update_status(request):
    user=check_validation(request)
    data='Kids Zone is Cool'
    if user:
        if request.method=="POST":
            form=StatusForm(request.POST)
            if form.is_valid():
                status=form.cleaned_data.get('status')
                user_name=user.username
                print user_name
                USER=User.objects.all().filter(username=user_name).first()
                USER.status=status
                # status_text=User(username=user_name,status=status)
                # status_text.save()
                # data=status
                print status +"is posted"

        return render(request,'feed.html',{

        })

    else:
        return redirect('/login/')


def feed_view(request):                 #view for feed.html
    user=check_validation(request)

    if user:
        all_posts = PostModel.objects.all().order_by('-created_on')
        page = request.GET.get('page', 1)
        paginator = Paginator(all_posts,10)
        try:
           posts= paginator.page(page)
        except PageNotAnInteger:
           posts = paginator.page(1)
        except EmptyPage:
           posts = paginator.page(paginator.num_pages)

        for post in posts:
            existing_like = LikeModel.objects.filter(post_id=post.id, user=user).first()
            if existing_like:
                post.has_liked = True
            for comment in post.comments:
                existing_upvote=CommentLikeModel.objects.filter(comment_id=comment.id,user=user).first()
                if existing_upvote:
                    comment.has_upvoted=True
                else:
                    comment.has_upvoted=False


        return render(request, "feed.html", {'posts': posts })
    else:
        return redirect('/login/')

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
def my_posts(request):    #view displaying the posts by a particular user
    USER=check_validation(request)
    if USER:
        user=User.objects.all().filter(username=USER.username).first()
        if user:
                posts = PostModel.objects.all().filter(user__username=user.username)
                return render(request, 'postsofuser.html', {'posts': posts, 'user_name': user.username})
        else:
            raise Http404

    else:
        return  redirect('/login/')

def profile_view(request):
    user = check_validation(request)
    if user:
        if request.method == "POST":
            form = ProfileForm(request.POST, request.FILES)
            if form.is_valid():
                image = form.cleaned_data.get('avatar')
                profile = User.objects.create(user=user, avatar=image)
                profile.save()
                path = str(BASE_DIR + profile.avatar.url)
                client = ImgurClient("6fc30e7f6bd87be", "0e21d82e47b11e66d7f6f3874cd269633c25c682")
                profile.image_url = client.upload_from_path(path, anon=True)['link']
                profile.save()
                return render(request,'error.html')
                app = ClarifaiApp(api_key=CLARIFAI_API_KEY)
                model = app.models.get('nsfw-v1.0')
                response = model.predict_by_url(url=profile.avatar_url)
                concepts_value = response['outputs'][0]['data']['concepts']
                for i in concepts_value:
                    if i['name'] == 'nsfw':
                        nudity_level = i['value']

                        if nudity_level >= 0.85:
                            print response['outputs'][0]['data']['concepts']
                            print nudity_level
                            profile.delete()
                            error_message = "You are trying to post an inappropriate photo!!"
                            return render(request, "error.html", {'error_message': error_message})
                        else:
                            return redirect('/feed/')
        else:
            form = PostForm()

        return render(request, "profile.html", {'form': form})
    else:
        return redirect('login')

def comment_view(request):
    user = check_validation(request)
    if user and request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            post_id = form.cleaned_data.get('post').id
            comment_text = str(form.cleaned_data.get('comment_text'))
            abusive_content = abuse(comment_text)
            print (abusive_content)
            if abusive_content['sentence_type'] == "Abusive":
                error_message = "You are trying to add an inapproprite comment!!"
                return render(request, 'error.html', {'error_message': error_message})  # redirecting to page displaying error if user tries to post an inapproprite comment
            else:

                comment = CommentModel.objects.create(user=user, post_id=post_id, comment_text=comment_text)
                comment.save()
                post = PostModel.objects.get(id=post_id)
                recipient_mail = post.user.email
                recipient_name = comment.user.username
                sending_mail(recipient_mail, content_text=recipient_name + " has commented on your post")
                return redirect('/feed/')
        else:
            return redirect('/feed/')
    else:
        return redirect('/login/')

def upvote_comment(request):
    user=check_validation(request)
    if user and request.method=="POST":
        form=CommentLikeForm(request.POST)
        if form.is_valid():
                comment_id = form.cleaned_data.get('comment').id
                existing_like = CommentLikeModel.objects.filter(comment_id=comment_id,user=user).first()
                if not existing_like:
                     CommentLikeModel.objects.create(comment_id=comment_id, user=user)
                     comment=CommentModel.objects.filter(id=comment_id).first()
                     print  comment.comment_text + "-comment upvoted"
                else:
                    existing_like.delete()
                    comment = CommentModel.objects.filter(id=comment_id).first()
                    print  comment.comment_text + "-comment downvoted"

        return redirect('/feed/')
    else:
        return redirect('/login/')



def check_validation(request):    #function to check the validation of session of user on every httprequest
    if request.COOKIES.get('session_token'):
        session = SessionToken.objects.filter(session_token=request.COOKIES.get('session_token')).first()
        if session:
            time_to_live = session.created_on + timedelta(days=1)
            if time_to_live > timezone.now():
                return session.user
    else:
        return None


def cancel_validation(request):    #function to cancel the validation of session token generated on logging out
    if request.COOKIES.get('session_token'):
        session = SessionToken.objects.filter(session_token=request.COOKIES.get('session_token')).first()
        if session:
            session.delete()
        else:
            pass


def sending_mail(recipient_mail,content_text):     #function to send mail using sendgrid api
    sg = sendgrid.SendGridAPIClient(apikey=SENDGRID_API_KEY)
    from_email = Email("kidszone@gmail.com")
    to_email = Email(recipient_mail)
    subject = "Notification from Kids Zone, a social networking site for kids!!"
    content = Content("text/plain", content_text)
    mail = Mail(from_email, subject, to_email, content)
    response = sg.client.mail.send.post(request_body=mail.get())