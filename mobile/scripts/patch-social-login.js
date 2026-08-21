#!/usr/bin/env node
/**
 * Capgo Social Login pulls androidx.browser:1.9.0 (Apple stub) and
 * androidbrowserhelper → browser:1.4.0 at the same time. Patch the plugin
 * gradle so Google-only builds resolve cleanly on compileSdk 35.
 */
const fs = require("fs");
const path = require("path");

const target = path.join(
  __dirname,
  "..",
  "node_modules",
  "@capgo",
  "capacitor-social-login",
  "android",
  "build.gradle"
);

if (!fs.existsSync(target)) {
  console.warn("[patch-social-login] plugin not installed, skip");
  process.exit(0);
}

let src = fs.readFileSync(target, "utf8");
if (src.includes("exclude group: 'androidx.browser'")) {
  console.log("[patch-social-login] already patched");
  process.exit(0);
}

const from = `    // Google dependencies
    if (googleDependencyType == 'compileOnly') {
        compileOnly 'com.google.android.gms:play-services-auth:21.4.0'
        compileOnly "androidx.credentials:credentials-play-services-auth:1.5.0"
        compileOnly "com.google.android.libraries.identity.googleid:googleid:1.1.1"
        compileOnly 'com.google.androidbrowserhelper:androidbrowserhelper:2.5.0'
    } else if (includeGoogle == 'true') {
        implementation 'com.google.android.gms:play-services-auth:21.4.0'
        implementation "androidx.credentials:credentials-play-services-auth:1.5.0"
        implementation "com.google.android.libraries.identity.googleid:googleid:1.1.1"
        implementation 'com.google.androidbrowserhelper:androidbrowserhelper:2.5.0'
    }
    
    // Facebook dependencies
    if (facebookDependencyType == 'compileOnly') {
        compileOnly 'com.facebook.android:facebook-login:18.1.3'
    } else if (includeFacebook == 'true') {
        implementation 'com.facebook.android:facebook-login:18.1.3'
    }
    
    // Apple dependencies
    if (appleDependencyType == 'compileOnly') {
        compileOnly "androidx.browser:browser:1.9.0"
    } else if (includeApple == 'true') {
        implementation "androidx.browser:browser:1.9.0"
    }`;

const to = `    // Google dependencies
    if (googleDependencyType == 'compileOnly') {
        compileOnly 'com.google.android.gms:play-services-auth:21.4.0'
        compileOnly "androidx.credentials:credentials-play-services-auth:1.5.0"
        compileOnly "com.google.android.libraries.identity.googleid:googleid:1.1.1"
        compileOnly('com.google.androidbrowserhelper:androidbrowserhelper:2.5.0') {
            exclude group: 'androidx.browser', module: 'browser'
        }
        compileOnly "androidx.browser:browser:1.8.0"
    } else if (includeGoogle == 'true') {
        implementation 'com.google.android.gms:play-services-auth:21.4.0'
        implementation "androidx.credentials:credentials-play-services-auth:1.5.0"
        implementation "com.google.android.libraries.identity.googleid:googleid:1.1.1"
        implementation('com.google.androidbrowserhelper:androidbrowserhelper:2.5.0') {
            exclude group: 'androidx.browser', module: 'browser'
        }
        implementation "androidx.browser:browser:1.8.0"
    }
    
    // Facebook dependencies
    if (facebookDependencyType == 'compileOnly') {
        compileOnly 'com.facebook.android:facebook-login:18.1.3'
    } else if (includeFacebook == 'true') {
        implementation 'com.facebook.android:facebook-login:18.1.3'
    }
    
    // Apple dependencies (only when enabled — disabled stubs must not pull browser 1.9.0)
    if (includeApple == 'true') {
        if (appleDependencyType == 'compileOnly') {
            compileOnly "androidx.browser:browser:1.8.0"
        } else {
            implementation "androidx.browser:browser:1.8.0"
        }
    }`;

if (!src.includes(from)) {
  console.error("[patch-social-login] unexpected plugin build.gradle — update scripts/patch-social-login.js");
  process.exit(1);
}

fs.writeFileSync(target, src.replace(from, to));
console.log("[patch-social-login] patched", target);
