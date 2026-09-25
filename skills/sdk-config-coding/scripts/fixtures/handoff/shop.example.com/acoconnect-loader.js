// SYNTHETIC TEST FIXTURE: not a real customer SDK. Shape mirrors an
// sdk-config-assistant output (acoConnectSdkConfig-example.js) renamed on handoff.
// pageView/productView passed; addToCart and loggedIn were escalated (empty enhance, no triggers).
(function () {
    function loadFromCDN(url) {
        return new Promise((resolve, reject) => {
            const s = document.createElement("script");
            s.src = url;
            s.onload = resolve;
            s.onerror = reject;
            document.head.appendChild(s);
        });
    }

    function configureSDK() {
        const config = window.TLT.getDefaultConfig();
        return config;
    }

    // InitLogsignsal here - do not remove this comment

    function initLogSignal() {
        const cfg = {
            fakeSignals: true,
            eventLog: false,
            errorLog: true,
            signalsLog: true,
            GAdataLayerName: "dataLayer",
            GAeventsAllowList: ["view_item"],
            messageTypes: ["dlListener"],
            signals: {
                pageView: {
                    signal: { signalType: "pageView", pageGroup: null },
                    triggers: [{ attributes: { type: 2 } }],
                    enhance(signal) {
                        signal.url = window.location.href;
                        signal.pageTitle = document.title;
                        return signal;
                    },
                },
                productView: {
                    signal: { signalType: "productView" },
                    triggers: [{ attributes: { "customEvent.name": "dlListener", "customEvent.data.event": "view_item" } }],
                    enhance(signal, help) {
                        const item = help.webEvent.customEvent.data.ecommerce.items[0];
                        signal.productId = item.item_id;
                        signal.productName = item.item_name;
                        signal.unitPrice = Number(item.price);
                        return signal;
                    },
                },
                addToCart: {
                    signal: { signalType: "addToCart" },
                    triggers: [],
                    enhance(signal) {
                        return signal;
                    },
                },
                loggedIn: {
                    signal: { signalType: "loggedIn" },
                    triggers: [],
                    enhance(signal) {
                        return signal;
                    },
                },
                audience: {
                    signal: {},
                    triggers: [{ attributes: { "event.type": "change", "target.id": "login-email" } }],
                    enhance(signal, help) {
                        const rawEmail = help.webEvent.target.currState.value;
                        if (help.validateEmailFormat(rawEmail)) help.store("audience", { Email: rawEmail });
                        return false;
                    },
                },
            },
        };
        return cfg;
    }
    window.initLogSignal = initLogSignal;

    async function initSDK() {
        if (window.TLT && typeof window.TLT.isInitialized === "function" && window.TLT.isInitialized()) {
            window.initLogSignal();
            return;
        }
        await loadFromCDN("https://sdk.example.invalid/acoconnect.js");
        TLT.initLibAdv({
            appKey: "EXAMPLE_APP_KEY",
            postUrl: "https://collector.example.invalid/collector",
            newConfig: configureSDK(),
            callback: window.initLogSignal,
        });
    }
    initSDK();
}());
