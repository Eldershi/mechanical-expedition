(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.SNBT = api;
  if (typeof window === "object") window.SNBT = api;
  if (typeof self === "object") self.SNBT = api;
})(typeof globalThis !== "undefined" ? globalThis : window, function () {
  "use strict";

  function number(value, suffix, raw) {
    const n = Number(value);
    const node = { __snbt: "number", value: Number.isFinite(n) ? n : 0, suffix: suffix || "" };
    if (raw) node.raw = raw;
    return node;
  }

  function typedArray(type, value) {
    return { __snbt: "typed_array", type, value: value || [] };
  }

  function isNumberNode(value) {
    return value && typeof value === "object" && value.__snbt === "number";
  }

  function isTypedArray(value) {
    return value && typeof value === "object" && value.__snbt === "typed_array";
  }

  function asNumber(value, fallback) {
    if (isNumberNode(value)) return value.value;
    if (typeof value === "number") return value;
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }

  class Parser {
    constructor(text) {
      this.text = text || "";
      this.i = 0;
    }

    parse() {
      this.ws();
      const value = this.value();
      this.ws();
      if (this.i < this.text.length) this.error("Unexpected trailing content");
      return value;
    }

    peek() {
      return this.text[this.i];
    }

    next() {
      return this.text[this.i++];
    }

    error(message) {
      const start = Math.max(0, this.i - 30);
      const end = Math.min(this.text.length, this.i + 30);
      throw new Error(`${message} at ${this.i}: ${this.text.slice(start, end).replace(/\s+/g, " ")}`);
    }

    ws() {
      while (this.i < this.text.length) {
        const c = this.peek();
        if (/\s/.test(c) || c === ",") {
          this.i++;
          continue;
        }
        if (c === "/" && this.text[this.i + 1] === "/") {
          while (this.i < this.text.length && this.peek() !== "\n") this.i++;
          continue;
        }
        if (c === "#" && this.text[this.i - 1] !== '"') {
          while (this.i < this.text.length && this.peek() !== "\n") this.i++;
          continue;
        }
        break;
      }
    }

    value() {
      this.ws();
      const c = this.peek();
      if (c === "{") return this.compound();
      if (c === "[") return this.list();
      if (c === '"' || c === "'") return this.string();
      return this.tokenValue();
    }

    compound() {
      const obj = Object.create(null);
      this.next();
      while (true) {
        this.ws();
        if (this.peek() === "}") {
          this.next();
          return obj;
        }
        const key = this.key();
        this.ws();
        if (this.next() !== ":") this.error("Expected ':' after key");
        obj[key] = this.value();
        this.ws();
      }
    }

    key() {
      this.ws();
      const c = this.peek();
      if (c === '"' || c === "'") return this.string();
      const start = this.i;
      while (this.i < this.text.length && !/[\s:{}\[\],]/.test(this.peek())) this.i++;
      if (this.i === start) this.error("Expected key");
      return this.text.slice(start, this.i);
    }

    list() {
      this.next();
      this.ws();
      const maybeType = this.peek();
      if ("BILbil".includes(maybeType) && this.text[this.i + 1] === ";") {
        this.i += 2;
        const values = [];
        while (true) {
          this.ws();
          if (this.peek() === "]") {
            this.next();
            return typedArray(maybeType.toUpperCase(), values);
          }
          values.push(this.value());
          this.ws();
        }
      }
      const arr = [];
      while (true) {
        this.ws();
        if (this.peek() === "]") {
          this.next();
          return arr;
        }
        arr.push(this.value());
        this.ws();
      }
    }

    string() {
      const quote = this.next();
      let out = "";
      while (this.i < this.text.length) {
        const c = this.next();
        if (c === quote) return out;
        if (c === "\\") {
          const e = this.next();
          if (e === "n") out += "\n";
          else if (e === "r") out += "\r";
          else if (e === "t") out += "\t";
          else out += e;
        } else {
          out += c;
        }
      }
      this.error("Unterminated string");
    }

    tokenValue() {
      const start = this.i;
      while (this.i < this.text.length && !/[\s{}\[\],]/.test(this.peek())) this.i++;
      const token = this.text.slice(start, this.i);
      if (!token) this.error("Expected value");
      if (token === "true") return true;
      if (token === "false") return false;
      if (/^[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?[bBsSlLfFdD]?$/.test(token)) {
        const match = token.match(/^(.+?)([bBsSlLfFdD])?$/);
        return number(match[1], match[2] || "", token);
      }
      return token;
    }
  }

  function parse(text) {
    return new Parser(text).parse();
  }

  function quoteString(value) {
    return `"${String(value).replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\n/g, "\\n").replace(/\r/g, "\\r").replace(/\t/g, "\\t")}"`;
  }

  function keyName(value) {
    return /^[A-Za-z_][A-Za-z0-9_.+-]*$/.test(value) ? value : quoteString(value);
  }

  function primitive(value) {
    return value == null || typeof value !== "object" || isNumberNode(value);
  }

  function formatNumber(value) {
    if (value.raw) return value.raw;
    const suffix = value.suffix || "";
    if (suffix.toLowerCase() === "d" || suffix.toLowerCase() === "f") {
      const n = Number(value.value);
      return `${Number.isInteger(n) ? n.toFixed(1) : String(n)}${suffix}`;
    }
    return `${Number(value.value)}${suffix}`;
  }

  function stringify(value, indent) {
    return write(value, indent || 0);
  }

  function write(value, indent) {
    const pad = "\t".repeat(indent);
    const child = "\t".repeat(indent + 1);
    if (typeof value === "string") return quoteString(value);
    if (typeof value === "boolean") return value ? "true" : "false";
    if (typeof value === "number") return String(value);
    if (isNumberNode(value)) return formatNumber(value);
    if (isTypedArray(value)) {
      if (!value.value.length) return `[${value.type};]`;
      return `[${value.type};\n${value.value.map((v) => `${child}${write(v, indent + 1)}`).join("\n")}\n${pad}]`;
    }
    if (Array.isArray(value)) {
      if (!value.length) return "[ ]";
      if (value.length <= 4 && value.every(primitive)) return `[${value.map((v) => write(v, indent)).join(" ")}]`;
      return `[\n${value.map((v) => `${child}${write(v, indent + 1)}`).join("\n")}\n${pad}]`;
    }
    if (value && typeof value === "object") {
      const entries = Object.entries(value);
      if (!entries.length) return "{ }";
      return `{\n${entries.map(([k, v]) => `${child}${keyName(k)}: ${write(v, indent + 1)}`).join("\n")}\n${pad}}`;
    }
    return "null";
  }

  return { parse, stringify, number, typedArray, isNumberNode, isTypedArray, asNumber };
});
