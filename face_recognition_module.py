# File: face_recognition_module.py

import face_recognition
import cv2
import numpy as np
import pickle
import os

class FaceRecognitionModule:
    def __init__(self, data_file='known_faces.pkl'):
        self.data_file = data_file
        self.known_face_encodings = []
        self.known_face_names = []
        self.load_known_faces()

    def load_known_faces(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'rb') as f:
                data = pickle.load(f)
                self.known_face_encodings = data['encodings']
                self.known_face_names = data['names']
            print(f"Loaded {len(self.known_face_names)} known faces")

    def save_known_faces(self):
        with open(self.data_file, 'wb') as f:
            pickle.dump({
                'encodings': self.known_face_encodings,
                'names': self.known_face_names
            }, f)
        print(f"Saved {len(self.known_face_names)} known faces")

    def add_face(self, image, name):
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        face_encodings = face_recognition.face_encodings(rgb_image)
        if face_encodings:
            self.known_face_encodings.append(face_encodings[0])
            self.known_face_names.append(name)
            self.save_known_faces()
            print(f"Debug: Face added for {name}")
            return True
        print(f"Debug: Failed to add face for {name}")
        return False

    def recognize_face(self, image):
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_image)
        print(f"Debug: Face locations detected: {face_locations}")
        
        face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
        print(f"Debug: Number of face encodings: {len(face_encodings)}")

        face_names = []
        for face_encoding in face_encodings:
            if not self.known_face_encodings:
                print("Debug: No known face encodings to compare against")
                name = "Unknown"
            else:
                matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
                print(f"Debug: Face matches: {matches}")
                name = "Unknown"

                face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                print(f"Debug: Face distances: {face_distances}")
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = self.known_face_names[best_match_index]
                    print(f"Debug: Face recognized as {name}")
                else:
                    print("Debug: Face not recognized")

            face_names.append(name)

        return face_locations, face_names

    def draw_faces(self, image, face_locations, face_names):
        for (top, right, bottom, left), name in zip(face_locations, face_names):
            cv2.rectangle(image, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.rectangle(image, (left, bottom - 35), (right, bottom), (0, 255, 0), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(image, name, (left + 6, bottom - 6), font, 0.5, (255, 255, 255), 1)
        return image