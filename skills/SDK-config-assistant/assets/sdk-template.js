(function () {
    function loadFromCDN(url) {
        return new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = url;
            script.onload = () => resolve();
            script.onerror = () => reject(new Error(`Failed to load ${url}`));
            document.head.appendChild(script);
        });
    }

    function configureSDK() {
        // Get the default config from the SDK core
        const config = window.TLT.getDefaultConfig();

        // Override core defaults
        config.core.buildNote = "Acoustic.com webApp Connect - 01 April 2026";
        config.core.modules.gestures.enabled = true;
        config.core.modules.ajaxListener.enabled = true;
        config.core.modules.dataLayer.enabled = false;
        config.core.frames = {
            enableCrossDomainCommunication: true,
            eventProducer: { producerId: "goAcoustic-com" },
            eventConsumer: { childFrameHostnameWhitelist: ["go.acoustic.com"] },
        }

        // Override services defaults
        config.services.queue.xhrEnabled = false;
        config.services.queue.queues[0].timerInterval = 30000;
        if (TLT.utils.isiOS || TLT.utils.isAndroid) {
            config.services.queue.queues[0].timerInterval = 10000;
        }
        config.services.message.privacy = [{
            exclude: true,
            targets: [
                "input[type=hidden]",
                "input[type=radio]",
                "input[type=checkbox]",
                "input[type=submit]",
                "input[type=button]",
                "input[type=reset]",
                "input[type=image]",
                "input[type=email]",
                "input[type=text]",
                "button",
                "[role=button]",
                { id: { regex: 'goAcoustic-com' }, idType: -2 }
            ], maskType: 2
        }];
        config.services.message.privacyPatterns = [];
        config.services.domCapture.options = { maxLength: 5000000 };
        config.services.browser.logAttributes = ["class", "id"];

        // Override modules defaults
        config.modules.performance.performanceAlert.blacklist = [{ regex: "brilliantcollector\\.com" }];
        config.modules.replay.domCapture.triggers = [
            { event: "change" },
            { event: "click" },
            { event: "dblclick" },
            { event: "contextmenu" },
            { event: "visibilitychange" },
            {
                event: "load",
                fullDOMCapture: true,
                delay: 300
            }
        ];
        config.modules.replay.mousemove.enabled = true;
        config.modules.ajaxListener = {
            blockNonJSONResponse: false,
            fieldBlocklist: [],
            urlBlocklist: [
                { regex: "brilliantcollector\\.com|clarity|collectorPost|crazyegg|doubleclick|google|yimg|cookielaw|stripe|subtotal|linkedin|aplo-evnt\\.com|app\\.qualified\\.com|content-us-1\\.content-cms\\.com", flags: "i" }
            ],
            filters: [
                {
                    url: { regex: "/secureLogin", flags: "i" },
                    status: { regex: "[45]\\d\\d" },
                    log: {
                        requestHeaders: true,
                        requestData: false,
                        responseHeaders: true,
                        responseData: true
                    }
                },
                {
                    status: { regex: "[45]\\d\\d" },
                    log: {
                        requestHeaders: true,
                        requestData: true,
                        responseHeaders: true,
                        responseData: true
                    }
                }
            ]
        };
        config.modules.TLCookie.secureTLTSID = true;
        return config;
    }

 // InitLogsignsal here - do not remove this comment

    window.initLogSignal = initLogSignal;
    async function initSDK() {
        if (window.__ACO_SDK_INIT_IN_PROGRESS || window.__ACO_SDK_INIT_DONE) {
            console.warn("[ACO] initSDK already invoked. Skipping duplicate call.");
            return;
        }
        window.__ACO_SDK_INIT_IN_PROGRESS = true;

        try {
            if (window.TLT && typeof window.TLT.isInitialized === "function" && window.TLT.isInitialized()) {
                console.warn("[ACO] TLT already initialized. Skipping initLibAdv and running initLogSignal only.");
                window.initLogSignal();
                window.__ACO_SDK_INIT_DONE = true;
                return;
            }

            console.log("[ACO] loading CDN...");
            await loadFromCDN("https://cdn.goacoustic.com/connect/latest/acoconnect.min.js");

            if (window.TLT && typeof window.TLT.isInitialized === "function" && window.TLT.isInitialized()) {
                console.warn("[ACO] TLT already initialized after CDN load. Skipping initLibAdv and running initLogSignal only.");
                window.initLogSignal();
                window.__ACO_SDK_INIT_DONE = true;
                return;
            }

            console.log("[ACO] calling initLibAdv...");
            TLT.initLibAdv({
                appKey: "%%APP_KEY%%",
                postUrl: "%%COLLECTOR_URL%%",
                newConfig: configureSDK(),
                addAjaxListener: true,
                callback: window.initLogSignal
            });
            window.__ACO_SDK_INIT_DONE = true;

        } catch (error) {
            console.error("[ACO] Failed to initialize:", error);
        } finally {
            window.__ACO_SDK_INIT_IN_PROGRESS = false;
        }
    }
    initSDK();
}());
