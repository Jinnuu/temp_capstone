// \0rolldown/runtime.js
var e = Object.create, t = Object.defineProperty, n = Object.getOwnPropertyDescriptor, r = Object.getOwnPropertyNames, i = Object.getPrototypeOf, a = Object.prototype.hasOwnProperty, o = (e, t) => () => (t || (e((t = { exports: {} }).exports, t, t.exports), e = null), t.exports), s = (e, i, o, s) => {
	if (i && typeof i == "object" || typeof i == "function") for (var c = r(i), l = 0, u = c.length, d; l < u; l++) d = c[l], !a.call(e, d) && d !== o && t(e, d, {
		get: ((e) => i[e]).bind(null, d),
		enumerable: !(s = n(i, d)) || s.enumerable
	});
	return e;
}, c = (n, r, o) => (o = n == null ? {} : e(i(n)), s(r || !n || !n.__esModule || !a.call(n, "default") ? t(o, "default", {
	value: n,
	enumerable: !0
}) : o, n)), l = /* @__PURE__ */ o(((e, t, n) => {
	(function(n, r) {
		typeof e == "object" && t !== void 0 ? t.exports = r() : typeof define == "function" && define.amd ? define(r) : (n = typeof globalThis < "u" ? globalThis : n || self, n.Data = r());
	})(n, (function() {
		let e = /* @__PURE__ */ new Map();
		return {
			set(t, n, r) {
				e.has(t) || e.set(t, /* @__PURE__ */ new Map());
				let i = e.get(t);
				!i.has(n) && i.size !== 0 ? console.error(`Bootstrap doesn't allow more than one instance per element. Bound instance: ${Array.from(i.keys())[0]}.`) : i.set(n, r);
			},
			get(t, n) {
				return e.has(t) && e.get(t).get(n) || null;
			},
			remove(t, n) {
				if (!e.has(t)) return;
				let r = e.get(t);
				r.delete(n), r.size === 0 && e.delete(t);
			}
		};
	}));
})), u = /* @__PURE__ */ o(((e, t, n) => {
	(function(n, r) {
		typeof e == "object" && t !== void 0 ? r(e) : typeof define == "function" && define.amd ? define(["exports"], r) : (n = typeof globalThis < "u" ? globalThis : n || self, r(n.Index = {}));
	})(n, (function(e) {
		let t = "transitionend", n = (e) => (e && window.CSS && window.CSS.escape && (e = e.replace(/#([^\s"#']+)/g, (e, t) => `#${CSS.escape(t)}`)), e), r = (e) => e == null ? `${e}` : Object.prototype.toString.call(e).match(/\s([a-z]+)/i)[1].toLowerCase(), i = (e) => {
			do
				e += Math.floor(Math.random() * 1e6);
			while (document.getElementById(e));
			return e;
		}, a = (e) => {
			if (!e) return 0;
			let { transitionDuration: t, transitionDelay: n } = window.getComputedStyle(e);
			return !Number.parseFloat(t) && !Number.parseFloat(n) ? 0 : (t = t.split(",")[0], n = n.split(",")[0], (Number.parseFloat(t) + Number.parseFloat(n)) * 1e3);
		}, o = (e) => {
			e.dispatchEvent(new Event(t));
		}, s = (e) => !e || typeof e != "object" ? !1 : (e.jquery !== void 0 && (e = e[0]), e.nodeType !== void 0), c = (e) => s(e) ? e.jquery ? e[0] : e : typeof e == "string" && e.length > 0 ? document.querySelector(n(e)) : null, l = (e) => {
			if (!s(e) || e.getClientRects().length === 0) return !1;
			let t = getComputedStyle(e).getPropertyValue("visibility") === "visible", n = e.closest("details:not([open])");
			if (!n) return t;
			if (n !== e) {
				let t = e.closest("summary");
				if (t && t.parentNode !== n || t === null) return !1;
			}
			return t;
		}, u = (e) => !e || e.nodeType !== Node.ELEMENT_NODE || e.classList.contains("disabled") ? !0 : e.disabled === void 0 ? e.hasAttribute("disabled") && e.getAttribute("disabled") !== "false" : e.disabled, d = (e) => {
			if (!document.documentElement.attachShadow) return null;
			if (typeof e.getRootNode == "function") {
				let t = e.getRootNode();
				return t instanceof ShadowRoot ? t : null;
			}
			return e instanceof ShadowRoot ? e : e.parentNode ? d(e.parentNode) : null;
		}, f = () => {}, p = (e) => {
			e.offsetHeight;
		}, m = () => window.jQuery && !document.body.hasAttribute("data-bs-no-jquery") ? window.jQuery : null, h = [], g = (e) => {
			document.readyState === "loading" ? (h.length || document.addEventListener("DOMContentLoaded", () => {
				for (let e of h) e();
			}), h.push(e)) : e();
		}, _ = () => document.documentElement.dir === "rtl", v = (e) => {
			g(() => {
				let t = m();
				/* istanbul ignore if */
				if (t) {
					let n = e.NAME, r = t.fn[n];
					t.fn[n] = e.jQueryInterface, t.fn[n].Constructor = e, t.fn[n].noConflict = () => (t.fn[n] = r, e.jQueryInterface);
				}
			});
		}, y = (e, t = [], n = e) => typeof e == "function" ? e(...t) : n;
		e.defineJQueryPlugin = v, e.execute = y, e.executeAfterTransition = (e, n, r = !0) => {
			if (!r) {
				y(e);
				return;
			}
			let i = a(n) + 5, s = !1, c = ({ target: r }) => {
				r === n && (s = !0, n.removeEventListener(t, c), y(e));
			};
			n.addEventListener(t, c), setTimeout(() => {
				s || o(n);
			}, i);
		}, e.findShadowRoot = d, e.getElement = c, e.getNextActiveElement = (e, t, n, r) => {
			let i = e.length, a = e.indexOf(t);
			return a === -1 ? !n && r ? e[i - 1] : e[0] : (a += n ? 1 : -1, r && (a = (a + i) % i), e[Math.max(0, Math.min(a, i - 1))]);
		}, e.getTransitionDurationFromElement = a, e.getUID = i, e.getjQuery = m, e.isDisabled = u, e.isElement = s, e.isRTL = _, e.isVisible = l, e.noop = f, e.onDOMContentLoaded = g, e.parseSelector = n, e.reflow = p, e.toType = r, e.triggerTransitionEnd = o, Object.defineProperty(e, Symbol.toStringTag, { value: "Module" });
	}));
})), d = /* @__PURE__ */ o(((e, t, n) => {
	(function(n, r) {
		typeof e == "object" && t !== void 0 ? t.exports = r(u()) : typeof define == "function" && define.amd ? define(["../util/index"], r) : (n = typeof globalThis < "u" ? globalThis : n || self, n.EventHandler = r(n.Index));
	})(n, (function(e) {
		let t = /[^.]*(?=\..*)\.|.*/, n = /\..*/, r = /::\d+$/, i = {}, a = 1, o = {
			mouseenter: "mouseover",
			mouseleave: "mouseout"
		}, s = /* @__PURE__ */ new Set(/* @__PURE__ */ "click.dblclick.mouseup.mousedown.contextmenu.mousewheel.DOMMouseScroll.mouseover.mouseout.mousemove.selectstart.selectend.keydown.keypress.keyup.orientationchange.touchstart.touchmove.touchend.touchcancel.pointerdown.pointermove.pointerup.pointerleave.pointercancel.gesturestart.gesturechange.gestureend.focus.blur.change.reset.select.submit.focusin.focusout.load.unload.beforeunload.resize.move.DOMContentLoaded.readystatechange.error.abort.scroll".split("."));
		function c(e, t) {
			return t && `${t}::${a++}` || e.uidEvent || a++;
		}
		function l(e) {
			let t = c(e);
			return e.uidEvent = t, i[t] = i[t] || {}, i[t];
		}
		function u(e, t) {
			return function n(r) {
				return y(r, { delegateTarget: e }), n.oneOff && v.off(e, r.type, t), t.apply(e, [r]);
			};
		}
		function d(e, t, n) {
			return function r(i) {
				let a = e.querySelectorAll(t);
				for (let { target: o } = i; o && o !== this; o = o.parentNode) for (let s of a) if (s === o) return y(i, { delegateTarget: o }), r.oneOff && v.off(e, i.type, t, n), n.apply(o, [i]);
			};
		}
		function f(e, t, n = null) {
			return Object.values(e).find((e) => e.callable === t && e.delegationSelector === n);
		}
		function p(e, t, n) {
			let r = typeof t == "string", i = r ? n : t || n, a = _(e);
			return s.has(a) || (a = e), [
				r,
				i,
				a
			];
		}
		function m(e, n, r, i, a) {
			if (typeof n != "string" || !e) return;
			let [s, m, h] = p(n, r, i);
			n in o && (m = ((e) => function(t) {
				if (!t.relatedTarget || t.relatedTarget !== t.delegateTarget && !t.delegateTarget.contains(t.relatedTarget)) return e.call(this, t);
			})(m));
			let g = l(e), _ = g[h] || (g[h] = {}), v = f(_, m, s ? r : null);
			if (v) {
				v.oneOff = v.oneOff && a;
				return;
			}
			let y = c(m, n.replace(t, "")), b = s ? d(e, r, m) : u(e, m);
			b.delegationSelector = s ? r : null, b.callable = m, b.oneOff = a, b.uidEvent = y, _[y] = b, e.addEventListener(h, b, s);
		}
		function h(e, t, n, r, i) {
			let a = f(t[n], r, i);
			a && (e.removeEventListener(n, a, !!i), delete t[n][a.uidEvent]);
		}
		function g(e, t, n, r) {
			let i = t[n] || {};
			for (let [a, o] of Object.entries(i)) a.includes(r) && h(e, t, n, o.callable, o.delegationSelector);
		}
		function _(e) {
			return e = e.replace(n, ""), o[e] || e;
		}
		let v = {
			on(e, t, n, r) {
				m(e, t, n, r, !1);
			},
			one(e, t, n, r) {
				m(e, t, n, r, !0);
			},
			off(e, t, n, i) {
				if (typeof t != "string" || !e) return;
				let [a, o, s] = p(t, n, i), c = s !== t, u = l(e), d = u[s] || {}, f = t.startsWith(".");
				if (o !== void 0) {
					if (!Object.keys(d).length) return;
					h(e, u, s, o, a ? n : null);
				} else {
					if (f) for (let n of Object.keys(u)) g(e, u, n, t.slice(1));
					for (let [n, i] of Object.entries(d)) {
						let a = n.replace(r, "");
						(!c || t.includes(a)) && h(e, u, s, i.callable, i.delegationSelector);
					}
				}
			},
			trigger(t, n, r) {
				if (typeof n != "string" || !t) return null;
				let i = e.getjQuery(), a = n !== _(n), o = null, s = !0, c = !0, l = !1;
				a && i && (o = i.Event(n, r), i(t).trigger(o), s = !o.isPropagationStopped(), c = !o.isImmediatePropagationStopped(), l = o.isDefaultPrevented());
				let u = y(new Event(n, {
					bubbles: s,
					cancelable: !0
				}), r);
				return l && u.preventDefault(), c && t.dispatchEvent(u), u.defaultPrevented && o && o.preventDefault(), u;
			}
		};
		function y(e, t = {}) {
			for (let [n, r] of Object.entries(t)) try {
				e[n] = r;
			} catch {
				Object.defineProperty(e, n, {
					configurable: !0,
					get() {
						return r;
					}
				});
			}
			return e;
		}
		return v;
	}));
})), f = /* @__PURE__ */ o(((e, t, n) => {
	(function(n, r) {
		typeof e == "object" && t !== void 0 ? t.exports = r() : typeof define == "function" && define.amd ? define(r) : (n = typeof globalThis < "u" ? globalThis : n || self, n.Manipulator = r());
	})(n, (function() {
		function e(e) {
			if (e === "true") return !0;
			if (e === "false") return !1;
			if (e === Number(e).toString()) return Number(e);
			if (e === "" || e === "null") return null;
			if (typeof e != "string") return e;
			try {
				return JSON.parse(decodeURIComponent(e));
			} catch {
				return e;
			}
		}
		function t(e) {
			return e.replace(/[A-Z]/g, (e) => `-${e.toLowerCase()}`);
		}
		return {
			setDataAttribute(e, n, r) {
				e.setAttribute(`data-bs-${t(n)}`, r);
			},
			removeDataAttribute(e, n) {
				e.removeAttribute(`data-bs-${t(n)}`);
			},
			getDataAttributes(t) {
				if (!t) return {};
				let n = {}, r = Object.keys(t.dataset).filter((e) => e.startsWith("bs") && !e.startsWith("bsConfig"));
				for (let i of r) {
					let r = i.replace(/^bs/, "");
					r = r.charAt(0).toLowerCase() + r.slice(1, r.length), n[r] = e(t.dataset[i]);
				}
				return n;
			},
			getDataAttribute(n, r) {
				return e(n.getAttribute(`data-bs-${t(r)}`));
			}
		};
	}));
})), p = /* @__PURE__ */ o(((e, t, n) => {
	(function(n, r) {
		typeof e == "object" && t !== void 0 ? t.exports = r(f(), u()) : typeof define == "function" && define.amd ? define(["../dom/manipulator", "./index"], r) : (n = typeof globalThis < "u" ? globalThis : n || self, n.Config = r(n.Manipulator, n.Index));
	})(n, (function(e, t) {
		class n {
			static get Default() {
				return {};
			}
			static get DefaultType() {
				return {};
			}
			static get NAME() {
				throw Error("You have to implement the static method \"NAME\", for each component!");
			}
			_getConfig(e) {
				return e = this._mergeConfigObj(e), e = this._configAfterMerge(e), this._typeCheckConfig(e), e;
			}
			_configAfterMerge(e) {
				return e;
			}
			_mergeConfigObj(n, r) {
				let i = t.isElement(r) ? e.getDataAttribute(r, "config") : {};
				return {
					...this.constructor.Default,
					...typeof i == "object" ? i : {},
					...t.isElement(r) ? e.getDataAttributes(r) : {},
					...typeof n == "object" ? n : {}
				};
			}
			_typeCheckConfig(e, n = this.constructor.DefaultType) {
				for (let [r, i] of Object.entries(n)) {
					let n = e[r], a = t.isElement(n) ? "element" : t.toType(n);
					if (!new RegExp(i).test(a)) throw TypeError(`${this.constructor.NAME.toUpperCase()}: Option "${r}" provided type "${a}" but expected type "${i}".`);
				}
			}
		}
		return n;
	}));
})), m = /* @__PURE__ */ o(((e, t, n) => {
	(function(n, r) {
		typeof e == "object" && t !== void 0 ? t.exports = r(l(), d(), p(), u()) : typeof define == "function" && define.amd ? define([
			"./dom/data",
			"./dom/event-handler",
			"./util/config",
			"./util/index"
		], r) : (n = typeof globalThis < "u" ? globalThis : n || self, n.BaseComponent = r(n.Data, n.EventHandler, n.Config, n.Index));
	})(n, (function(e, t, n, r) {
		class i extends n {
			constructor(t, n) {
				super(), t = r.getElement(t), t && (this._element = t, this._config = this._getConfig(n), e.set(this._element, this.constructor.DATA_KEY, this));
			}
			dispose() {
				e.remove(this._element, this.constructor.DATA_KEY), t.off(this._element, this.constructor.EVENT_KEY);
				for (let e of Object.getOwnPropertyNames(this)) this[e] = null;
			}
			_queueCallback(e, t, n = !0) {
				r.executeAfterTransition(e, t, n);
			}
			_getConfig(e) {
				return e = this._mergeConfigObj(e, this._element), e = this._configAfterMerge(e), this._typeCheckConfig(e), e;
			}
			static getInstance(t) {
				return e.get(r.getElement(t), this.DATA_KEY);
			}
			static getOrCreateInstance(e, t = {}) {
				return this.getInstance(e) || new this(e, typeof t == "object" ? t : null);
			}
			static get VERSION() {
				return "5.3.3";
			}
			static get DATA_KEY() {
				return `bs.${this.NAME}`;
			}
			static get EVENT_KEY() {
				return `.${this.DATA_KEY}`;
			}
			static eventName(e) {
				return `${e}${this.EVENT_KEY}`;
			}
		}
		return i;
	}));
})), h = /* @__PURE__ */ o(((e, t, n) => {
	(function(n, r) {
		typeof e == "object" && t !== void 0 ? t.exports = r(u()) : typeof define == "function" && define.amd ? define(["../util/index"], r) : (n = typeof globalThis < "u" ? globalThis : n || self, n.SelectorEngine = r(n.Index));
	})(n, (function(e) {
		let t = (t) => {
			let n = t.getAttribute("data-bs-target");
			if (!n || n === "#") {
				let e = t.getAttribute("href");
				if (!e || !e.includes("#") && !e.startsWith(".")) return null;
				e.includes("#") && !e.startsWith("#") && (e = `#${e.split("#")[1]}`), n = e && e !== "#" ? e.trim() : null;
			}
			return n ? n.split(",").map((t) => e.parseSelector(t)).join(",") : null;
		}, n = {
			find(e, t = document.documentElement) {
				return [].concat(...Element.prototype.querySelectorAll.call(t, e));
			},
			findOne(e, t = document.documentElement) {
				return Element.prototype.querySelector.call(t, e);
			},
			children(e, t) {
				return [].concat(...e.children).filter((e) => e.matches(t));
			},
			parents(e, t) {
				let n = [], r = e.parentNode.closest(t);
				for (; r;) n.push(r), r = r.parentNode.closest(t);
				return n;
			},
			prev(e, t) {
				let n = e.previousElementSibling;
				for (; n;) {
					if (n.matches(t)) return [n];
					n = n.previousElementSibling;
				}
				return [];
			},
			next(e, t) {
				let n = e.nextElementSibling;
				for (; n;) {
					if (n.matches(t)) return [n];
					n = n.nextElementSibling;
				}
				return [];
			},
			focusableChildren(t) {
				let n = [
					"a",
					"button",
					"input",
					"textarea",
					"select",
					"details",
					"[tabindex]",
					"[contenteditable=\"true\"]"
				].map((e) => `${e}:not([tabindex^="-"])`).join(",");
				return this.find(n, t).filter((t) => !e.isDisabled(t) && e.isVisible(t));
			},
			getSelectorFromElement(e) {
				let r = t(e);
				return r && n.findOne(r) ? r : null;
			},
			getElementFromSelector(e) {
				let r = t(e);
				return r ? n.findOne(r) : null;
			},
			getMultipleElementsFromSelector(e) {
				let r = t(e);
				return r ? n.find(r) : [];
			}
		};
		return n;
	}));
})), g = /* @__PURE__ */ o(((e, t, n) => {
	(function(n, r) {
		typeof e == "object" && t !== void 0 ? r(e, d(), h(), u()) : typeof define == "function" && define.amd ? define([
			"exports",
			"../dom/event-handler",
			"../dom/selector-engine",
			"./index"
		], r) : (n = typeof globalThis < "u" ? globalThis : n || self, r(n.ComponentFunctions = {}, n.EventHandler, n.SelectorEngine, n.Index));
	})(n, (function(e, t, n, r) {
		e.enableDismissTrigger = (e, i = "hide") => {
			let a = `click.dismiss${e.EVENT_KEY}`, o = e.NAME;
			t.on(document, a, `[data-bs-dismiss="${o}"]`, function(t) {
				if (["A", "AREA"].includes(this.tagName) && t.preventDefault(), r.isDisabled(this)) return;
				let a = n.getElementFromSelector(this) || this.closest(`.${o}`);
				e.getOrCreateInstance(a)[i]();
			});
		}, Object.defineProperty(e, Symbol.toStringTag, { value: "Module" });
	}));
})), _ = /* @__PURE__ */ c((/* @__PURE__ */ o(((e, t, n) => {
	(function(n, r) {
		typeof e == "object" && t !== void 0 ? t.exports = r(m(), d(), g(), u()) : typeof define == "function" && define.amd ? define([
			"./base-component",
			"./dom/event-handler",
			"./util/component-functions",
			"./util/index"
		], r) : (n = typeof globalThis < "u" ? globalThis : n || self, n.Alert = r(n.BaseComponent, n.EventHandler, n.ComponentFunctions, n.Index));
	})(n, (function(e, t, n, r) {
		let i = ".bs.alert", a = `close${i}`, o = `closed${i}`;
		class s extends e {
			static get NAME() {
				return "alert";
			}
			close() {
				if (t.trigger(this._element, a).defaultPrevented) return;
				this._element.classList.remove("show");
				let e = this._element.classList.contains("fade");
				this._queueCallback(() => this._destroyElement(), this._element, e);
			}
			_destroyElement() {
				this._element.remove(), t.trigger(this._element, o), this.dispose();
			}
			static jQueryInterface(e) {
				return this.each(function() {
					let t = s.getOrCreateInstance(this);
					if (typeof e == "string") {
						if (t[e] === void 0 || e.startsWith("_") || e === "constructor") throw TypeError(`No method named "${e}"`);
						t[e](this);
					}
				});
			}
		}
		return n.enableDismissTrigger(s, "close"), r.defineJQueryPlugin(s), s;
	}));
})))(), 1), v = (e) => Number.isInteger(e) && e >= 1 && e <= 6;
function y(e) {
	if (!e || typeof e != "object" || Array.isArray(e) || !v(e.current)) return {
		current: 1,
		completed: []
	};
	let t = Array.isArray(e.completed) ? [...new Set(e.completed.filter(v))].sort((e, t) => e - t) : [];
	return {
		current: e.current,
		completed: t
	};
}
function b(e) {
	let t = y(e);
	return y({
		...t,
		completed: [...t.completed, t.current]
	});
}
function x(e, t) {
	let n = y(e);
	return {
		...n,
		current: Math.max(1, Math.min(6, n.current + (t === -1 ? -1 : 1)))
	};
}
function S(e) {
	return Math.round(y(e).completed.length / 6 * 100);
}
function C(e) {
	return /^\d+$/.test(e) ? `snp.guide.nutritionist.v1.${e}` : null;
}
// src/guide.ts
function w() {
	let e = document.querySelector("[data-guide]");
	e && T(e);
}
function T(e) {
	e.dataset.guideEnhanced = "true";
	let t = e.querySelector("[data-guide-index]"), n = document.documentElement.dataset.snpPreview === "true", r = C(e.dataset.progressKey?.split(".").pop() || ""), i = y(null), a = !0, o = e.querySelector("[data-guide-status]");
	if (!n && r) try {
		let e = localStorage.getItem(r);
		e && (i = y(JSON.parse(e)));
	} catch {
		a = !1;
	}
	let s = Array.from(e.querySelectorAll("[data-guide-step]")), c = Array.from(e.querySelectorAll("[data-guide-go]"));
	function l() {
		if (!n && r) try {
			localStorage.setItem(r, JSON.stringify(i));
		} catch {
			a = !1;
		}
	}
	function u(t = !1) {
		let r = i.current;
		e.dataset.guideStorage = a ? "ok" : "blocked";
		for (let e of s) {
			let t = Number(e.dataset.guideStep) === r;
			e.hidden = !t, e.open = t, e.classList.toggle("is-current", t);
		}
		for (let e of c) {
			let t = Number(e.dataset.guideGo);
			e.toggleAttribute("data-read", i.completed.includes(t)), t === r ? e.setAttribute("aria-current", "step") : e.removeAttribute("aria-current");
		}
		let l = e.querySelector("[data-guide-progress]");
		l && (l.value = i.completed.length);
		let u = e.querySelector("[data-guide-progress-text]");
		u && (u.textContent = `읽은 단계 ${i.completed.length} / 6 (${S(i)}%)`);
		let d = e.querySelector("[data-guide-prev]");
		d && (d.disabled = n || r === 1);
		let f = e.querySelector("[data-guide-next]");
		f && (f.disabled = n || r === 6);
		let p = e.querySelector("[data-guide-read]");
		p && (p.setAttribute("aria-pressed", String(i.completed.includes(r))), p.textContent = i.completed.includes(r) ? "이해했어요 ✓" : "이해했어요"), o && (o.textContent = a ? i.completed.length === 6 ? "6단계를 모두 읽었어요. 실제 업무는 각 화면에서 확인하고 저장하세요." : `${r}단계예요. 읽었다면 이해했어요를 눌러 주세요.` : "브라우저 저장을 사용할 수 없어 현재 화면에서만 진행합니다. 업무 메뉴는 정상 이용할 수 있습니다."), t && s[r - 1]?.querySelector("h2")?.focus();
	}
	function d(e, n = !1) {
		i = y({
			...i,
			current: e
		}), l(), t && !n && (t.open = !1), u(!n);
	}
	for (let e of c) e.addEventListener("click", () => d(Number(e.dataset.guideGo))), e.addEventListener("keydown", (e) => {
		[
			"ArrowLeft",
			"ArrowRight",
			"Home",
			"End"
		].includes(e.key) && (e.preventDefault(), d(e.key === "Home" ? 1 : e.key === "End" ? 6 : x(i, e.key === "ArrowLeft" ? -1 : 1).current, !0), c[i.current - 1]?.focus());
	});
	for (let e of s) e.querySelector("summary")?.addEventListener("click", (t) => {
		t.preventDefault();
		let n = Number(e.dataset.guideStep);
		n === i.current ? e.open = !e.open : d(n);
	});
	e.querySelector("[data-guide-prev]")?.addEventListener("click", () => d(x(i, -1).current)), e.querySelector("[data-guide-next]")?.addEventListener("click", () => d(x(i, 1).current)), e.querySelector("[data-guide-read]")?.addEventListener("click", () => {
		i = b(i), l(), u();
	}), e.querySelector("[data-guide-reset]")?.addEventListener("click", () => {
		i = y(null), l(), t && (t.open = !1), u(!0);
	}), u();
}
// src/brand.ts
var E = {
	status: "confirmed",
	source: "사용자 확인: 영양사 프로그램 ZIP의 업무형 구조에 초록색 적용. 별도 포스터 없음.",
	accent: "#286447",
	accentText: "#24553d"
}, D = [
	"reference",
	"green",
	"civic"
], O = (e) => typeof e == "string" && D.includes(e), k = {
	reference: "레퍼런스형",
	green: "그린형",
	civic: "공공기관형"
}, A = document.documentElement, j = A.dataset.snpPreview === "true", M = O(A.dataset.snpMode) ? A.dataset.snpMode : "reference";
A.dataset.greenStatus = E.status, E.status === "confirmed" && E.accent && E.accentText && (A.style.setProperty("--green-accent", E.accent), A.style.setProperty("--green-accent-text", E.accentText));
function N(e, t) {
	M = e, A.dataset.snpMode = e, document.querySelectorAll("[data-ui-mode]").forEach((t) => {
		let n = t.dataset.uiMode === e;
		t.setAttribute("aria-pressed", String(n));
	});
	let n = `${k[e]}로 전환했습니다. 입력 중인 내용은 유지됩니다.`;
	if (t && !j) try {
		localStorage.setItem("snp.ui.mode.v1", e);
	} catch {
		n += " 현재 브라우저에서는 선택을 저장할 수 없습니다.";
	}
	let r = document.querySelector("#snp-mode-status");
	r && (r.textContent = n);
}
N(M, !1), document.querySelectorAll("[data-ui-mode]").forEach((e) => {
	e.addEventListener("click", () => {
		let t = e.dataset.uiMode;
		O(t) && N(t, !0);
	}), e.addEventListener("keydown", (e) => {
		if (![
			"ArrowLeft",
			"ArrowRight",
			"Home",
			"End"
		].includes(e.key)) return;
		e.preventDefault();
		let t = D.indexOf(M), n = e.key === "Home" ? D[0] : e.key === "End" ? D[2] : D[(t + (e.key === "ArrowRight" ? 1 : 2)) % 3];
		N(n, !0), document.querySelector(`[data-ui-mode="${n}"]`)?.focus();
	});
}), window.addEventListener("storage", (e) => {
	!j && e.key === "snp.ui.mode.v1" && O(e.newValue) && N(e.newValue, !1);
});
var P = document.querySelector("#snp-nav-toggle"), F = document.querySelector("#snp-navigation");
function I() {
	A.dataset.mobileNav = "false", P?.setAttribute("aria-expanded", "false");
}
P?.addEventListener("click", () => {
	let e = A.dataset.mobileNav !== "true";
	A.dataset.mobileNav = String(e), P.setAttribute("aria-expanded", String(e));
}), document.addEventListener("keydown", (e) => {
	e.key === "Escape" && A.dataset.mobileNav === "true" && (I(), P?.focus());
}), F?.addEventListener("click", (e) => {
	e.target.closest("a") && I();
});
var L = window.location.pathname;
document.querySelectorAll(".snp-navigation a").forEach((e) => {
	new URL(e.href).pathname === L && (e.setAttribute("aria-current", "page"), e.closest("details")?.setAttribute("open", ""));
});
var R = document.querySelectorAll(".snp-nav details");
document.querySelector(".snp-nav details[open]") || R[0]?.setAttribute("open", ""), R.forEach((e) => {
	e.addEventListener("pointerenter", () => {
		M === "reference" && window.innerWidth > 960 && (e.open = !0);
	}), e.addEventListener("pointerleave", () => {
		M === "reference" && window.innerWidth > 960 && !e.contains(document.activeElement) && (e.open = !1);
	});
});
var z = document.querySelector("#snp-workspace"), B = z?.querySelector("h1"), V = document.querySelector("#snp-current-page");
V && (V.textContent = B?.textContent?.trim() || document.title.split("|")[0].trim()), z && (z.querySelectorAll("table").forEach((e, t) => {
	if (e.parentElement?.closest("table") || e.parentElement?.classList.contains("snp-table-frame")) return;
	let n = document.createElement("div");
	n.className = "snp-table-frame", n.tabIndex = 0, n.setAttribute("role", "region"), n.setAttribute("aria-label", `${B?.textContent?.trim() || "업무"} 표 ${t + 1} 가로 스크롤`), e.before(n), n.append(e);
}), z.querySelectorAll(".errorlist").forEach((e) => e.setAttribute("role", "alert")), j && (z.querySelectorAll("input,select,textarea,button").forEach((e) => e.disabled = !0), z.addEventListener("submit", (e) => e.preventDefault(), !0), document.addEventListener("click", (e) => {
	e.target.closest("a") && e.preventDefault();
}, !0))), document.querySelectorAll(".alert[data-dismissible],.alert-dismissible").forEach((e) => _.default.getOrCreateInstance(e));
var H = document.querySelector("#snp-compare-page");
H?.addEventListener("change", () => {
	[
		"/",
		"/procurement/workflow/",
		"/procurement/workflow/headcounts/",
		"/inventory/ingredients/",
		"/meals/mealplan/weekly/",
		"/procurement/workflow/ledger/",
		"/meals/cooking/"
	].includes(H.value) && document.querySelectorAll("[data-snp-preview-mode]").forEach((e) => e.src = H.value + "?snp_preview=1");
});
var U = document.querySelector(".fresh-supplier-fields"), W = document.querySelectorAll("input[name=signup_type]");
if (U && W.length) {
	let e = () => {
		U.open = Array.from(W).some((e) => e.checked && e.value === "SUPPLIER");
	};
	W.forEach((t) => t.addEventListener("change", e)), e();
}
w();
