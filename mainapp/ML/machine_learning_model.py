import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
import pickle

def train_and_save_model():
    # 파일 경로
    file_path = '../DailyDoodle_ML/teset.xlsx'  # 절대 경로 사용

    # 엑셀 파일 읽기
    data = pd.read_excel(file_path, engine='openpyxl')

    # 텍스트 데이터와 감정 레이블 추출
    text_data = data['사람문장1'].dropna()  # 결측값 제거
    emotion_labels = data['감정_대분류'][text_data.index]

    # 감정 레이블 인코딩
    label_encoder = LabelEncoder()
    encoded_labels = label_encoder.fit_transform(emotion_labels)

    # 텍스트 데이터 벡터화 (TF-IDF)
    vectorizer = TfidfVectorizer(max_features=5000)
    X = vectorizer.fit_transform(text_data).toarray()

    # 학습 데이터와 테스트 데이터로 분할
    X_train, X_test, y_train, y_test = train_test_split(X, encoded_labels, test_size=0.2, random_state=42)

    # 로지스틱 회귀 모델 학습
    model = LogisticRegression()
    model.fit(X_train, y_train)

    # 모델 평가
    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred, target_names=label_encoder.classes_))

    # 모델과 벡터라이저 저장
    with open('sentiment_model.pkl', 'wb') as model_file:
        pickle.dump(model, model_file)

    with open('vectorizer.pkl', 'wb') as vectorizer_file:
        pickle.dump(vectorizer, vectorizer_file)

    with open('label_encoder.pkl', 'wb') as label_encoder_file:
        pickle.dump(label_encoder, label_encoder_file)

if __name__ == '__main__':
    train_and_save_model()
