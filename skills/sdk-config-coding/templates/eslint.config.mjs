import globals from "globals";
import path from "path";
import { fileURLToPath } from "url";
import js from "@eslint/js";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const compat = new FlatCompat({
    baseDirectory: __dirname,
    recommendedConfig: js.configs.recommended,
    allConfig: js.configs.all
});

export default [
    // Requires "eslint-config-airbnb" package to be loaded in compatibility mode
    ...compat.extends("airbnb-base"),
    // Do not lint this file as it uses ES6 modules and technically import isn't
    // allowed, although it works fine, so long as the file extension is .mjs
    { ignores: ["eslint.config.mjs"] },
    // Do not lint the Releases folder
    { ignores: ["node_modules", "assets", ".claude"] },
    {
        languageOptions: {
            globals: {
                // Import standard browser global variables
                ...globals.browser,
                // Commonly used UIC objects as globals
                TLT: "readonly",
                dataLayer: "readonly",
                WebAnalytics: "readonly",
                Cust: "readonly",
                importScripts: "readonly",
                pako: "readonly",
                prestashop: "readonly"
            },
            // We no longer support IE11
            ecmaVersion: 2020,
            sourceType: "script",
        },

        rules: {
            // Ignore parameter reassignment in common cases
            "no-param-reassign": ["error", {
                props: true,
                ignorePropertyModificationsFor: [
                    "element",
                    "targetObj",
                    "domCapture",
                    "msgObj",
                    "headers",
                    "xhr",
                    "obj",
                    "msg",
                    "signal",
                    "thisSig"
                ],
            }],
            // Ignore underscore dangle in common cases
            "no-underscore-dangle": ["error", {
                allow: [
                    "_xhr",
                    "_vis_opt_experiment_id",
                    "_vwo_exp",
                    "_getQueue",
                    "__isProxied",
                    "__tempDataLayer",
                    "__istrackingPush",
                    "cache_"
                ]
            }],
            // Ignore unused vars in common cases
            "no-unused-vars": ["error", { "argsIgnorePattern": "^signal$|^help$|^event$", "varsIgnorePattern": "^configureSDK$|^targetSDK$|^initLogSignal$" }],
            quotes: ["error", "double", { avoidEscape: true }], // Prefer double quotes
            indent: ["error", 4], // Indent 4 spaces
            "one-var": ["error", { var: "consecutive", let: "never", const: "never" }],
            "brace-style": ["error", "1tbs", { allowSingleLine: true }], // 1tbs curly braces style
            "object-shorthand": ["error", "never"],
            "func-names": ["error", "never"],
            strict: "off",
            "prefer-destructuring": "off",
            "no-console": "off",
            radix: ["error", "as-needed"],
            "max-len": "off",
            "comma-dangle": ["error", "only-multiline"],
            "no-var": "off",
            "no-multi-spaces": ["error", { ignoreEOLComments: true }],
            "prefer-rest-params": "off",
            "no-plusplus": ["error", { allowForLoopAfterthoughts: true }],
            "no-continue": "off",
            "prefer-template": "off",
            "prefer-arrow-callback": "off",
            "wrap-iife": ["error", "outside"],
            "prefer-object-spread": "off",
            "linebreak-style": "off",
            "no-multi-assign": ["error", { ignoreNonDeclaration: true }],
            "padded-blocks": ["error", "never"],
            "prefer-spread": "off",
            "no-cond-assign": ["error", "except-parens"],
            camelcase: ["error", { allow: ["TLT_custom"] }],
            // "consistent-return": "off"
            // "object-property-newline": ["error", { allowAllPropertiesOnSameLine: false }],
            // "object-curly-newline": ["error", { multiline: true, minProperties: 3, consistent: true }],
            "object-curly-newline": "off",
            "object-property-newline": ["error", { "allowAllPropertiesOnSameLine": true }],
            "array-bracket-newline": ["error", { "minItems": 2 }],
            "array-element-newline": ["error", { "minItems": 2 }],
            "no-restricted-syntax": ["off", "ForOfStatement"]
        },
    }
];
