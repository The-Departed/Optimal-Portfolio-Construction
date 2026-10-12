// Display formatting only. Financial calculations belong to the backend.

const percent = new Intl.NumberFormat("en-IN", {
  style: "percent",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const decimal = new Intl.NumberFormat("en-IN", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 4,
});

const dateFmt = new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" });
const dateTimeFmt = new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" });

export const formatPercent = (value: number) => percent.format(value);
export const formatDecimal = (value: number) => decimal.format(value);
export const formatDate = (iso: string) => dateFmt.format(new Date(iso));
export const formatDateTime = (iso: string) => dateTimeFmt.format(new Date(iso));

const percentPrecise = new Intl.NumberFormat("en-IN", {
  style: "percent",
  minimumFractionDigits: 3,
  maximumFractionDigits: 3,
});
const fixed2 = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const integer = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

/** Daily returns are small: show three decimals of a percent (e.g. 0.028%). */
export const formatPercentPrecise = (value: number) => percentPrecise.format(value);
export const formatFixed2 = (value: number) => fixed2.format(value);
export const formatInteger = (value: number) => integer.format(value);
/** Formats an optional statistic, showing an em dash when the backend reports none. */
export const orDash = (value: number | null | undefined, fmt: (v: number) => string) =>
  value === null || value === undefined ? "—" : fmt(value);

const percent0 = new Intl.NumberFormat("en-IN", { style: "percent", maximumFractionDigits: 1 });
/** Axis ticks: whole percents (one decimal only when needed). */
export const formatPercentTick = (value: number) => percent0.format(value);
