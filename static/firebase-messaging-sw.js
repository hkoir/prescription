importScripts('/static/firebase/firebase-app.js');
importScripts('/static/firebase/firebase-messaging.js');

firebase.initializeApp({
  apiKey: "AIzaSyCcGjdQ-W19cFFFsJ55Ha7pcyzJNPM_w_U",
  authDomain: "prescription-7d74b.firebaseapp.com",
  projectId: "prescription-7d74b",
  storageBucket: "prescription-7d74b.appspot.com",
  messagingSenderId: "70620825982",
  appId: "1:70620825982:web:8329d7f949b6a2cfc04b2f",
  measurementId: "G-0KM6605DXK"
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage(function(payload) {
  console.log('[firebase-messaging-sw.js] Received background message ', payload);
  const notificationTitle = payload.notification.title;
  const notificationOptions = {
    body: payload.notification.body,
    icon: '/static/images/icons/patient.png' // or your app icon
  };

  self.registration.showNotification(notificationTitle, notificationOptions);
});
