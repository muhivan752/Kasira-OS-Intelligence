export type FirebaseWebConfig = { apiKey: string; authDomain: string; projectId: string; appId: string };

export async function prepareGoogleAuth(config: FirebaseWebConfig) {
  const [{ initializeApp, getApps }, sdk] = await Promise.all([
    import('firebase/app'), import('firebase/auth'),
  ]);
  const app = getApps().find(app => app.name === 'selaris-auth') || initializeApp(config, 'selaris-auth');
  const auth = sdk.getAuth(app);
  await sdk.setPersistence(auth, sdk.inMemoryPersistence);
  return { auth, sdk };
}

export async function googleIdToken(config: FirebaseWebConfig): Promise<string> {
  const { auth, sdk } = await prepareGoogleAuth(config);
  const provider = new sdk.GoogleAuthProvider();
  provider.setCustomParameters({ prompt: 'select_account' });
  const result = await sdk.signInWithPopup(auth, provider);
  return result.user.getIdToken();
}
