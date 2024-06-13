from rest_framework import generics, status
from django.contrib.auth.models import User as DjangoUser  # Django의 기본 User 모델
from .serializers import UserSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
import requests
from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings
import pickle
import os
from .models import Diary
from django.db import IntegrityError

class UserListView(generics.ListAPIView):
    queryset = DjangoUser.objects.all()  # Django의 기본 User 모델 사용
    serializer_class = UserSerializer

class UserDetailView(generics.RetrieveAPIView):
    queryset = DjangoUser.objects.all()  # Django의 기본 User 모델 사용
    serializer_class = UserSerializer

class SignUpAPI(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def spotify_login(request):
    client_id = settings.SPOTIFY_CLIENT_ID
    redirect_uri = settings.SPOTIFY_REDIRECT_URI
    scope = 'user-read-private user-read-email'
    return redirect(f'https://accounts.spotify.com/authorize?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&scope={scope}')

def spotify_callback(request):
    code = request.GET.get('code')
    client_id = settings.SPOTIFY_CLIENT_ID
    client_secret = settings.SPOTIFY_CLIENT_SECRET
    redirect_uri = settings.SPOTIFY_REDIRECT_URI

    response = requests.post('https://accounts.spotify.com/api/token', data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri,
        'client_id': client_id,
        'client_secret': client_secret,
    }, verify=False)

    response_data = response.json()
    access_token = response_data.get('access_token')

    if not access_token:
        return JsonResponse({'error': 'Failed to retrieve access token from Spotify'}, status=400)

    user_info_response = requests.get('https://api.spotify.com/v1/me', headers={
        'Authorization': f'Bearer {access_token}'
    }, verify=False)
    user_info = user_info_response.json()

    spotify_id = user_info.get('id')
    email = user_info.get('email')
    username = user_info.get('display_name', email.split('@')[0])

    user, created = DjangoUser.objects.get_or_create(username=username, defaults={'email': email})
    if created:
        user.set_unusable_password()
        user.save()

    # user_id를 클라이언트에 전달
    response = redirect('http://localhost:3000/diary?access_token=' + access_token)
    response.set_cookie('user_id', user.id)  # user_id를 쿠키로 설정

    return response

class DiaryEntryAPI(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        model_path = os.path.join(os.path.dirname(__file__), 'sentiment_model.pkl')
        vectorizer_path = os.path.join(os.path.dirname(__file__), 'vectorizer.pkl')
        label_encoder_path = os.path.join(os.path.dirname(__file__), 'label_encoder.pkl')

        with open(model_path, 'rb') as model_file:
            self.model = pickle.load(model_file)

        with open(vectorizer_path, 'rb') as vectorizer_file:
            self.vectorizer = pickle.load(vectorizer_file)

        with open(label_encoder_path, 'rb') as label_encoder_file:
            self.label_encoder = pickle.load(label_encoder_file)

    def post(self, request):
        text = request.data.get('text')
        user_id = request.data.get('user_id')

        if not text:
            return Response({'error': 'No text provided'}, status=status.HTTP_400_BAD_REQUEST)
        if not user_id:
            return Response({'error': 'No user ID provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = DjangoUser.objects.get(id=user_id)  # Django의 기본 User 모델 사용
        except DjangoUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            text_vectorized = self.vectorizer.transform([text]).toarray()
            predicted_emotion_index = self.model.predict(text_vectorized)
            predicted_emotion = self.label_encoder.inverse_transform(predicted_emotion_index)
        except Exception as e:
            return Response({'error': 'Error during emotion prediction', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            diary_entry = Diary(user=user, text=text, mood=predicted_emotion[0])
            diary_entry.save()
        except Exception as e:
            return Response({'error': 'Error saving diary entry', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'result': predicted_emotion[0]}, status=status.HTTP_200_OK)
