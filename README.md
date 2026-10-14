# Dex Hub tvOS

**Kodi for Apple TV with the Aether player and Dex Hub built in.**
Dolby Vision, HDR10, Dolby Atmos, Arabic subtitles, and the Dex Hub interface in one app.

> **Unofficial build.** Not made or supported by Team Kodi or the XBMC Foundation.
> Kodi® is a registered trademark of the XBMC Foundation.

[العربية](#بالعربي) · [English](#english)

---

## بالعربي

### ما هو
تطبيق Kodi 22 معدّل لـ Apple TV، فيه:
- **مشغل Aether 7.35.1** افتراضي: Dolby Vision وHDR10 وHLG حسب المصدر والشاشة، H.264 وHEVC وAV1، ومطابقة معدل الإطارات تلقائيا.
- **Dolby Atmos:** صيغة E-AC-3 JOC تلقائيا. صيغة TrueHD Atmos تتحول إلى صوت مكاني (APAC) يخرج كـ Dolby MAT، وتختار توزيع سماعاتك من الإعدادات (5.1.2 إلى 9.1.6). هذا ليس تمرير TrueHD خام.
- **ثلاثة خيارات تشغيل:** Aether، ومشغل Kodi الأصلي، أو تطبيق خارجي (Infuse أو VidHub) مع تمرير الوقت والترجمة والعودة.
- **إضافة Dex Hub وسكين Dex Hub** مثبتة داخل التطبيق من أول تشغيل، مع خطوط عربية للترجمة.
- **أداء:** بناء Release، والواجهة على معدل Apple TV نفسه (60Hz).

### المتطلبات
- Apple TV 4K بنظام **tvOS 26** أو أحدث.
- للتثبيت: أداة توقيع وحساب Apple (تفاصيلها تحت).
- للبناء من السورس فقط: ماك Apple Silicon مع Xcode 26 أو أحدث، و20 GB مساحة فاضية على الأقل.

### ⚠️ التطبيق يحتاج توقيع
ملف IPA في صفحة Releases **غير موقّع**. Apple TV لا يقبل تثبيت تطبيق غير موقّع، فلازم توقّعه أنت بحسابك قبل التثبيت:

1. حمّل `Kodi-DexHub-AetherOnly-*-unsigned.ipa` من [Releases](../../releases).
2. وقّعه بأداة توقيع تدعم Apple TV، مثل Sideloadly أو أي أداة تستخدمها، بحساب Apple:
   - **حساب Apple مجاني:** التوقيع ينتهي بعد 7 أيام وتعيد التوقيع.
   - **حساب مطوّر مدفوع:** التوقيع سنة كاملة.
3. **وقّع التطبيق كامل مع مجلد Frameworks.** فيه مكتبات Aether وFFmpeg، وأي مكتبة غير موقّعة توقف التثبيت.
4. لتحديث نسخة مثبتة بدون ما تفقد بياناتك، استخدم نفس معرّف التطبيق (Bundle ID) ونفس الحساب.

**لو ظهر خطأ** `ApplicationVerificationFailed ... invalid signature` على أحد ملفات `Aether*.framework`، شغّل على الماك:
```bash
bash FIX-SIGNING.command /path/to/file.ipa
```
يطلع ملف جديد ينتهي بـ `-fixed.ipa`، وقّعه وثبّته. الإصدارات من v20 فما فوق تطلع جاهزة بدون هذه الخطوة.

### البناء من السورس (ماك)
أول مرة على الماك (ينزل Kodi 22 RC1 ويبني اعتمادياته مرة واحدة، ويطول):
```bash
git clone https://github.com/6ahd/DexHub-tvOS.git ~/Developer/DexHub-tvOS/DexHub-tvOS
bash ~/Developer/DexHub-tvOS/DexHub-tvOS/update-kodi.sh 22.0rc1-Piers
```
بعدها أي بناء جديد:
```bash
bash ~/Developer/DexHub-tvOS/DexHub-tvOS/BUILD.command
```
الناتج في Downloads باسم `Kodi-DexHub-AetherOnly-v20-TEST-unsigned-<وقت>.ipa`، ثم وقّعه كما فوق.

ما يسويه البناء:
1. ينزل محرك Aether 7.35.1 ويثبت إصدارات مكتباته (FFmpegBuild وLibDovi وLibTrueHD وSMBClient).
2. يبني جسر Swift صغير (`DexAetherEmbedded.swift`) يربط Aether بـ Kodi.
3. يطبّق تعديلات Kodi من مجلد `native/` عبر `apply_bridge.py`، مع نسخة احتياطية، ويقدر يرجعها.
4. يبني Kodi بوضع Release، ويضيف الإضافات من `assets/`، ويجهّز المكتبات للتوقيع، ثم يطلع IPA.

إضافة Dex Hub والسكين ينزلون تلقائيا من Releases عن طريق `get-dexhub.sh`.

### الحقوق
- سكربتات البناء وتعديلات Kodi وجسر Aether في هذا المستودع: **GPL-2.0-or-later**، © 2026 DexWorld.
- **إضافة Dex Hub وسكين Dex Hub ليست ضمن هذا الترخيص.** تُنشر كملفات إصدار فقط، ولكل واحد ترخيصه داخل ملفه. إعادة توزيع إضافة Dex Hub أو تعديلها أو بيعها تحتاج إذنا مكتوبا.
- المكونات الأخرى لها تراخيصها، والتفاصيل في [NOTICE.md](NOTICE.md).

---

## English

### What it is
A modified Kodi 22 for Apple TV with:
- **Aether 7.35.1** as the default player: Dolby Vision, HDR10 and HLG (source and display permitting), H.264, HEVC and AV1, automatic frame rate matching.
- **Dolby Atmos:** E-AC-3 JOC automatically. TrueHD Atmos is rendered to Apple spatial audio (APAC) and output as Dolby MAT, with your real speaker layout picked in settings (5.1.2 to 9.1.6). This is not raw TrueHD passthrough.
- **Three ways to play:** Aether, Kodi's own player, or an external app (Infuse or VidHub) with resume, subtitle hand-off and return.
- **Dex Hub add-on and skin** installed on first launch, with Arabic subtitle fonts.
- **Performance:** Release build; the interface runs in the Apple TV's own mode (60 Hz).

### Requirements
- Apple TV 4K on **tvOS 26** or later.
- To install: a signing tool and an Apple account (see below).
- To build from source only: an Apple Silicon Mac with Xcode 26 or later and at least 20 GB free.

### ⚠️ The app must be signed
The IPA on the Releases page is **unsigned**. Apple TV will not install an unsigned app, so you sign it yourself before installing:

1. Download `Kodi-DexHub-AetherOnly-*-unsigned.ipa` from [Releases](../../releases).
2. Sign it with an Apple TV capable signing tool (Sideloadly or whatever you use) and an Apple account:
   - **Free Apple account:** the signature expires after 7 days; sign again.
   - **Paid developer account:** valid for a year.
3. **Sign the whole app including the Frameworks folder.** It carries the Aether and FFmpeg libraries; one unsigned library stops the install.
4. To update an installed copy and keep its data, use the same bundle ID and account.

**If you get** `ApplicationVerificationFailed ... invalid signature` on an `Aether*.framework`, run on a Mac:
```bash
bash FIX-SIGNING.command /path/to/file.ipa
```
Sign and install the `-fixed.ipa` it writes. Builds from v20 on do this already.

### Build from source (Mac)
First time on a Mac (downloads Kodi 22 RC1 and builds its dependencies once; this takes a while):
```bash
git clone https://github.com/6ahd/DexHub-tvOS.git ~/Developer/DexHub-tvOS/DexHub-tvOS
bash ~/Developer/DexHub-tvOS/DexHub-tvOS/update-kodi.sh 22.0rc1-Piers
```
Every build after that:
```bash
bash ~/Developer/DexHub-tvOS/DexHub-tvOS/BUILD.command
```
The unsigned IPA lands in Downloads; sign it as above.

The build pins Aether 7.35.1 (commit `60ac862`) and its packages, builds the small Swift bridge, applies the Kodi changes in `native/` through `apply_bridge.py` (with a backup and `--restore`), builds Kodi in Release, bundles the add-ons in `assets/`, prepares the frameworks for signing and writes the IPA. The Dex Hub add-on and skin are fetched from Releases by `get-dexhub.sh`.

### Licence
- Build scripts, Kodi changes and the Aether bridge in this repository: **GPL-2.0-or-later**, © 2026 DexWorld.
- **The Dex Hub add-on and skin are not covered by this licence.** They are published as release files only, each with its own licence inside. Redistributing, modifying or selling the Dex Hub add-on needs written permission.
- Other components keep their own licences; see [NOTICE.md](NOTICE.md).
