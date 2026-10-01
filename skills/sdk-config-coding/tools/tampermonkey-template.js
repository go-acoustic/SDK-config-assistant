// ==UserScript==
// @name         Acoustic Connect - HOSTNAME
// @namespace    acoustic-connect
// @version      1.0
// @description  Injects the Acoustic Connect SDK loader for development
// @author       Acoustic
// @match        https://MATCH_PATTERN
// @require      file://ABSOLUTE_PROJECT_PATH/sites/HOSTNAME/acoconnect-loader.js
// @grant        none
// @noframes
// ==/UserScript==

// NOTE: Before adding this script in Tampermonkey:
//   1. Replace HOSTNAME with the site hostname (e.g. shop.acmeretail.com)
//   2. Replace MATCH_PATTERN with the appropriate URL pattern (e.g. shop.acmeretail.com/*)
//      Use a wildcard subdomain prefix if needed (e.g. *.northwindtrading.co.uk*/*)
//   3. Replace ABSOLUTE_PROJECT_PATH with the absolute path of the current project directory
//      (run `pwd` there — do not guess it), then replace HOSTNAME in that same line too
//   4. Reload the page to pick up changes to the loader — Tampermonkey re-reads file:// @require on each load

(function () {
    'use strict';
}());
