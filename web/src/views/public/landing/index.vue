<template>
	<div class="landing">
		<header class="nav">
			<div class="nav-inner">
				<router-link to="/welcome" class="brand" aria-label="proNotify home">
					<img :src="logo" alt="proNotify" />
				</router-link>
				<nav class="nav-links" aria-label="Main navigation">
					<a href="#features" @click.prevent="scrollTo('features')">Features</a>
					<a href="#how-it-works" @click.prevent="scrollTo('how-it-works')">How it works</a>
					<a href="#pricing" @click.prevent="scrollTo('pricing')">Pricing</a>
					<a href="#checkout" @click.prevent="scrollTo('checkout')">Checkout</a>
					<a href="#contact" @click.prevent="scrollTo('contact')">Contact</a>
				</nav>
				<div class="nav-actions">
					<router-link to="/login" class="btn ghost">Sign in</router-link>
					<router-link to="/checkout" class="btn primary">Get started</router-link>
				</div>
			</div>
		</header>

		<main>
			<section class="hero">
				<div class="hero-inner">
					<div class="hero-copy">
						<span class="eyebrow">Built for Thai rental agents</span>
						<h1>Rent reminders that reach your LINE group — automatically.</h1>
						<p class="lead">
							proNotify keeps every room, lease, rent cycle and document in one place, then sends the right reminder to the right LINE group and syncs your Google Calendar. No more manual follow-ups.
						</p>
						<div class="hero-actions">
							<router-link to="/checkout" class="btn primary lg">Start annual plan — {{ formatTHB(plan.priceTHB) }}</router-link>
							<router-link to="/login" class="btn ghost lg">Sign in</router-link>
						</div>
						<p class="micro">
							One-time annual payment · {{ plan.billingDays }} days · No auto-renewal · {{ plan.paymentMethod }}
						</p>
						<p class="thai">
							ระบบแจ้งเตือนค่าเช่าอัตโนมัติสำหรับนายหน้าอสังหาริมทรัพย์ในประเทศไทย<br />
							แพ็กเกจรายปี ฿{{ plan.priceTHB.toLocaleString('en-US') }} ต่อ {{ plan.billingDays }} วัน · ชำระครั้งเดียว · ไม่ต่ออายุอัตโนมัติ
						</p>
					</div>
					<div class="hero-card" aria-label="Product preview">
						<div class="preview-head">
							<span class="dot red"></span><span class="dot yellow"></span><span class="dot green"></span>
							<span class="preview-title">Today’s reminders</span>
						</div>
						<div class="preview-row">
							<span class="preview-ico">R</span>
							<div>
								<b>Rent reminder · Room A1</b>
								<small>LINE group · Owner + tenant + agent</small>
							</div>
							<span class="pill ok">Sent</span>
						</div>
						<div class="preview-row">
							<span class="preview-ico">E</span>
							<div>
								<b>Lease expiry · Room B2</b>
								<small>30 days before end date · Google Calendar synced</small>
							</div>
							<span class="pill ok">Sent</span>
						</div>
						<div class="preview-row">
							<span class="preview-ico">C</span>
							<div>
								<b>Custom reminder · Room C3</b>
								<small>Monthly utility reminder · 12th</small>
							</div>
							<span class="pill pending">Queued</span>
						</div>
						<div class="preview-foot">
							<span>500 messages / month included</span>
							<span>TH · EN · 中文</span>
						</div>
					</div>
				</div>
			</section>

			<section id="features" class="section">
				<div class="section-head">
					<span class="eyebrow">Everything in one workspace</span>
					<h2>Designed for the way rental agents already work</h2>
					<p>Less spreadsheet chasing. More reliable follow-ups for every room you manage.</p>
				</div>
				<div class="feature-grid">
					<article class="feature">
						<span class="feature-ico">01</span>
						<h3>LINE group reminders</h3>
						<p>Connect a LINE group to each property and send rent, expiry and custom reminders automatically on the day they matter.</p>
					</article>
					<article class="feature">
						<span class="feature-ico">02</span>
						<h3>Property & lease records</h3>
						<p>Keep room name, rent, payment cycle, reminder day, lease dates, owner and notes in one shared record.</p>
					</article>
					<article class="feature">
						<span class="feature-ico">03</span>
						<h3>Google Calendar sync</h3>
						<p>Every property can be mirrored to Google Calendar so your team sees rent and expiry events alongside their day.</p>
					</article>
					<article class="feature">
						<span class="feature-ico">04</span>
						<h3>Group document storage</h3>
						<p>Contracts, invoices and photos shared in LINE groups can be stored and searched from the proNotify workspace.</p>
					</article>
					<article class="feature">
						<span class="feature-ico">05</span>
						<h3>Roles & tenant isolation</h3>
						<p>Managers, supervisors and staff see only the data they should. Each agency has its own isolated workspace.</p>
					</article>
					<article class="feature">
						<span class="feature-ico">06</span>
						<h3>Multi-language interface</h3>
						<p>Switch between English, Thai and Chinese so every member of your team can use the workspace comfortably.</p>
					</article>
				</div>
			</section>

			<section id="how-it-works" class="section alt">
				<div class="section-head">
					<span class="eyebrow">Simple setup</span>
					<h2>From sign-up to your first automated reminder</h2>
				</div>
				<ol class="steps">
					<li>
						<span class="step-num">1</span>
						<h3>Create your agency account</h3>
						<p>Sign up with your email, verify your address and choose your company name.</p>
					</li>
					<li>
						<span class="step-num">2</span>
						<h3>Pay for {{ plan.billingDays }} days</h3>
						<p>Scan the PromptPay QR on the checkout page. Payment is processed securely by Omise. No card details are stored by proNotify.</p>
					</li>
					<li>
						<span class="step-num">3</span>
						<h3>Add properties and LINE groups</h3>
						<p>Enter rent, payment cycle, reminder day, lease dates and the LINE group ID for each room.</p>
					</li>
					<li>
						<span class="step-num">4</span>
						<h3>Let proNotify do the follow-up</h3>
						<p>The daily scheduler scans your records and sends reminders to the linked LINE group and Google Calendar.</p>
					</li>
				</ol>
			</section>

			<section id="pricing" class="section">
				<div class="section-head">
					<span class="eyebrow">Clear pricing in Thai Baht</span>
					<h2>One annual plan. No hidden add-ons.</h2>
					<p>Prices are shown in Thai Baht (THB). The amount on your checkout page is the final amount charged.</p>
				</div>
				<div class="pricing-wrap">
					<div class="price-card">
						<div class="price-top">
							<span class="plan-name">{{ plan.name }}</span>
							<span class="plan-badge">{{ plan.billingDays }} days</span>
						</div>
						<div class="price">
							<span class="currency">฿</span>
							<span class="amount">{{ plan.priceTHB.toLocaleString('en-US') }}</span>
							<span class="per">THB / year</span>
						</div>
						<p class="price-desc">A one-time annual payment for your agency workspace. This plan does <b>not</b> renew automatically.</p>
						<ul class="price-list">
							<li>Unlimited property records</li>
							<li>Automated LINE group reminders</li>
							<li>Google Calendar sync</li>
							<li>Group document storage</li>
							<li>Manager, supervisor and staff roles</li>
							<li>500 LINE messages per month included</li>
						</ul>
						<router-link to="/checkout" class="btn primary wide">Continue to checkout</router-link>
						<p class="price-note">Payment method: {{ plan.paymentMethod }}</p>
					</div>
					<div class="terms-card">
						<h3>Subscription & auto-renewal terms</h3>
						<dl>
							<div>
								<dt>Billing cycle</dt>
								<dd>{{ plan.billingDays }} days from the date your payment is confirmed.</dd>
							</div>
							<div>
								<dt>Price</dt>
								<dd>{{ formatTHB(plan.priceTHB) }} (Thai Baht) per {{ plan.billingDays }}-day term.</dd>
							</div>
							<div>
								<dt>Auto-renewal</dt>
								<dd><b>No auto-renewal.</b> proNotify does not store your payment details and will not charge you automatically. Your plan simply ends after {{ plan.billingDays }} days.</dd>
							</div>
							<div>
								<dt>How to renew</dt>
								<dd>You can manually buy another {{ plan.billingDays }}-day term at any time from your account. We will remind you before expiry.</dd>
							</div>
							<div>
								<dt>How to cancel</dt>
								<dd>Email {{ BUSINESS.email }} at least 7 days before the end of your current term. Cancellation stops the next renewal. Access continues until the end of the paid term.</dd>
							</div>
						</dl>
						<div class="legal-links">
							<a :href="LEGAL_LINKS.terms">Terms of Service</a>
							<a :href="LEGAL_LINKS.refund">Cancellation & Refund Policy</a>
							<a :href="LEGAL_LINKS.privacy">Privacy Policy</a>
						</div>
					</div>
				</div>
			</section>

			<section id="checkout" class="section alt">
				<div class="section-head">
					<span class="eyebrow">Checkout</span>
					<h2>Review your plan before you pay</h2>
					<p>This is the order summary shown before secure payment. Payment is completed after account verification.</p>
				</div>
				<div class="checkout-card">
					<div class="checkout-product">
						<div>
							<b>{{ plan.name }}</b>
							<small>{{ plan.billingDays }}-day access · one-time payment · no auto-renewal</small>
						</div>
						<span class="checkout-price">{{ formatTHB(plan.priceTHB) }}</span>
					</div>
					<div class="checkout-lines">
						<div><span>Billing period</span><b>{{ plan.billingDays }} days</b></div>
						<div><span>Payment method</span><b>{{ plan.paymentMethod }}</b></div>
						<div><span>Auto-renewal</span><b>Not enabled</b></div>
						<div><span>Currency</span><b>THB (Thai Baht)</b></div>
					</div>
					<div class="checkout-total">
						<span>Total due today</span>
						<b>{{ formatTHB(plan.priceTHB) }}</b>
					</div>
					<div class="checkout-actions">
						<router-link to="/checkout" class="btn primary wide">Open checkout</router-link>
						<router-link to="/signup" class="btn ghost wide">Create an account first</router-link>
					</div>
					<p class="checkout-fine">
						By continuing you agree to our
						<a :href="LEGAL_LINKS.terms">Terms of Service</a>,
						<a :href="LEGAL_LINKS.refund">Cancellation & Refund Policy</a>
						and <a :href="LEGAL_LINKS.privacy">Privacy Policy</a>.
					</p>
				</div>
			</section>

			<section id="contact" class="section">
				<div class="section-head">
					<span class="eyebrow">Contact us</span>
					<h2>Talk to the team behind proNotify</h2>
					<p>Questions about billing, cancellation, privacy or onboarding? We are here to help.</p>
				</div>
				<div class="contact-grid">
					<div class="contact-card">
						<h3>Business details</h3>
						<dl>
							<div><dt>Legal name</dt><dd>{{ BUSINESS.legalName }}</dd></div>
							<div><dt>Contact person</dt><dd>{{ BUSINESS.contactName }}</dd></div>
							<div><dt>Address</dt><dd>{{ BUSINESS.address }}</dd></div>
							<div><dt>Phone</dt><dd>{{ BUSINESS.phone }}</dd></div>
							<div><dt>Email</dt><dd><a :href="`mailto:${BUSINESS.email}`">{{ BUSINESS.email }}</a></dd></div>
							<div><dt>Support hours</dt><dd>{{ BUSINESS.hours }}</dd></div>
						</dl>
					</div>
					<div class="contact-card">
						<h3>Policies</h3>
						<p>Please read these before purchasing a plan. They explain how the service works, how we handle personal data and how to request a refund.</p>
						<ul class="policy-list">
							<li><a :href="LEGAL_LINKS.terms">Terms of Service <span>→</span></a></li>
							<li><a :href="LEGAL_LINKS.refund">Cancellation & Refund Policy <span>→</span></a></li>
							<li><a :href="LEGAL_LINKS.privacy">Privacy Policy <span>→</span></a></li>
							<li><a :href="LEGAL_LINKS.contact">Contact & Billing Information <span>→</span></a></li>
						</ul>
						<router-link to="/checkout" class="btn primary">Start checkout</router-link>
					</div>
				</div>
			</section>
		</main>

		<footer class="footer">
			<div class="footer-inner">
				<div class="footer-brand">
					<img :src="logo" alt="proNotify" />
					<p>Automated rent reminders for Thai rental agents.</p>
				</div>
				<div class="footer-cols">
					<div>
						<b>Product</b>
						<a href="#features" @click.prevent="scrollTo('features')">Features</a>
						<a href="#pricing" @click.prevent="scrollTo('pricing')">Pricing</a>
						<a href="#checkout" @click.prevent="scrollTo('checkout')">Checkout</a>
					</div>
					<div>
						<b>Legal</b>
						<a :href="LEGAL_LINKS.terms">Terms of Service</a>
						<a :href="LEGAL_LINKS.privacy">Privacy Policy</a>
						<a :href="LEGAL_LINKS.refund">Refund & Cancellation</a>
					</div>
					<div>
						<b>Contact</b>
						<a :href="`mailto:${BUSINESS.email}`">{{ BUSINESS.email }}</a>
						<a :href="LEGAL_LINKS.contact">Contact details</a>
						<router-link to="/login">Sign in</router-link>
					</div>
				</div>
			</div>
			<div class="footer-bottom">
				<span>© 2026–2028 proNotify. All rights reserved.</span>
				<span>{{ BUSINESS.legalName }} · {{ BUSINESS.address }}</span>
			</div>
		</footer>
	</div>
</template>

<script setup lang="ts" name="publicLanding">
import { onMounted, ref } from 'vue';
import logo from '/@/assets/img/proNotify_logo_trans.png';
import { NextLoading } from '/@/utils/loading';
import { BUSINESS, PLAN, LEGAL_LINKS, formatTHB, fetchPublicPlan } from '/@/views/public/business';

const plan = ref({ ...PLAN });

const scrollTo = (id: string) => {
	document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
};

onMounted(async () => {
	NextLoading.done();
	document.title = 'proNotify — LINE Rent Reminders & Property Management for Thai Rental Agents';
	plan.value = await fetchPublicPlan();
});
</script>

<style scoped lang="scss">
.landing {
	--pn-bg: #1f1f1f;
	--pn-bg-alt: #171718;
	--pn-card: #1a1a1c;
	--pn-card-2: #222225;
	--pn-border: #333337;
	--pn-text: #e8e8ea;
	--pn-muted: #b1b4b8;
	--pn-faint: #8f9297;
	--pn-primary: #409eff;
	--pn-primary-hover: #66b1ff;
	--pn-green: #67c23a;

	min-height: 100dvh;
	background: var(--pn-bg);
	color: var(--pn-text);
	font-family: 'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans Thai', sans-serif;
	font-size: 15px;
	line-height: 1.65;
}

.landing a {
	color: inherit;
	text-decoration: none;
}

.nav {
	position: sticky;
	top: 0;
	z-index: 20;
	background: rgba(31, 31, 31, 0.88);
	border-bottom: 1px solid rgba(255, 255, 255, 0.06);
	backdrop-filter: blur(14px);
}

.nav-inner {
	display: flex;
	align-items: center;
	gap: 28px;
	max-width: 1180px;
	margin: 0 auto;
	padding: 16px 24px;
}

.brand img {
	display: block;
	width: 150px;
	height: auto;
}

.nav-links {
	display: flex;
	gap: 22px;
	margin-left: 10px;
	font-size: 14px;
	color: var(--pn-muted);
}

.nav-links a:hover {
	color: var(--pn-text);
}

.nav-actions {
	display: flex;
	gap: 10px;
	margin-left: auto;
}

.btn {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	gap: 8px;
	border: 1px solid transparent;
	border-radius: 10px;
	padding: 10px 18px;
	font-size: 14px;
	font-weight: 600;
	line-height: 1.2;
	white-space: nowrap;
	transition: background 0.18s ease, border-color 0.18s ease, transform 0.18s ease;
	cursor: pointer;
}

.btn:hover {
	transform: translateY(-1px);
}

.btn.primary {
	background: var(--pn-primary);
	border-color: var(--pn-primary);
	color: #fff;
}

.btn.primary:hover {
	background: var(--pn-primary-hover);
	border-color: var(--pn-primary-hover);
}

.btn.ghost {
	background: transparent;
	border-color: var(--pn-border);
	color: var(--pn-text);
}

.btn.ghost:hover {
	border-color: #4a4a50;
	background: rgba(255, 255, 255, 0.04);
}

.btn.lg {
	padding: 14px 24px;
	font-size: 15px;
}

.btn.wide {
	width: 100%;
}

.hero {
	border-bottom: 1px solid rgba(255, 255, 255, 0.06);
	background:
		radial-gradient(900px 420px at 18% 0%, rgba(64, 158, 255, 0.16), transparent 65%),
		radial-gradient(700px 360px at 92% 18%, rgba(103, 194, 58, 0.09), transparent 70%);
}

.hero-inner {
	display: grid;
	grid-template-columns: minmax(0, 1.1fr) minmax(360px, 0.9fr);
	gap: 56px;
	align-items: center;
	max-width: 1180px;
	margin: 0 auto;
	padding: 84px 24px 96px;
}

.eyebrow {
	display: inline-block;
	margin-bottom: 14px;
	color: #8ec5ff;
	font-size: 12px;
	font-weight: 700;
	letter-spacing: 0.12em;
	text-transform: uppercase;
}

.hero h1 {
	max-width: 760px;
	margin: 0;
	font-size: clamp(36px, 5vw, 62px);
	line-height: 1.08;
	letter-spacing: -0.03em;
}

.lead {
	max-width: 660px;
	margin: 22px 0 0;
	color: var(--pn-muted);
	font-size: 17px;
	line-height: 1.8;
}

.hero-actions {
	display: flex;
	flex-wrap: wrap;
	gap: 12px;
	margin-top: 30px;
}

.micro {
	margin: 16px 0 0;
	color: var(--pn-faint);
	font-size: 13px;
}

.thai {
	margin: 22px 0 0;
	color: #9fb0bd;
	font-size: 14px;
}

.hero-card {
	background: linear-gradient(180deg, #202024, #18181a);
	border: 1px solid var(--pn-border);
	border-radius: 18px;
	box-shadow: 0 28px 90px rgba(0, 0, 0, 0.45);
	overflow: hidden;
}

.preview-head {
	display: flex;
	align-items: center;
	gap: 7px;
	padding: 14px 18px;
	border-bottom: 1px solid rgba(255, 255, 255, 0.07);
	background: rgba(255, 255, 255, 0.025);
}

.dot {
	width: 9px;
	height: 9px;
	border-radius: 99px;
	display: block;
}

.dot.red { background: #ff5f57; }
.dot.yellow { background: #febc2e; }
.dot.green { background: #28c840; }

.preview-title {
	margin-left: 8px;
	color: var(--pn-faint);
	font-size: 12px;
	font-weight: 600;
	letter-spacing: 0.08em;
	text-transform: uppercase;
}

.preview-row {
	display: flex;
	align-items: center;
	gap: 14px;
	padding: 18px;
	border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.preview-row b {
	display: block;
	font-size: 14px;
	font-weight: 600;
}

.preview-row small {
	display: block;
	margin-top: 3px;
	color: var(--pn-faint);
	font-size: 12px;
}

.preview-ico {
	flex: 0 0 auto;
	display: grid;
	place-items: center;
	width: 34px;
	height: 34px;
	border-radius: 9px;
	background: rgba(64, 158, 255, 0.15);
	border: 1px solid rgba(64, 158, 255, 0.3);
	color: #9ec9ff;
	font-size: 12px;
	font-weight: 700;
}

.pill {
	margin-left: auto;
	flex: 0 0 auto;
	border-radius: 99px;
	padding: 4px 9px;
	font-size: 11px;
	font-weight: 700;
}

.pill.ok {
	background: rgba(103, 194, 58, 0.14);
	border: 1px solid rgba(103, 194, 58, 0.35);
	color: #9be37a;
}

.pill.pending {
	background: rgba(230, 162, 60, 0.12);
	border: 1px solid rgba(230, 162, 60, 0.3);
	color: #f3c777;
}

.preview-foot {
	display: flex;
	justify-content: space-between;
	gap: 16px;
	padding: 14px 18px;
	color: var(--pn-faint);
	font-size: 11px;
}

.section {
	max-width: 1180px;
	margin: 0 auto;
	padding: 88px 24px;
}

.section.alt {
	max-width: none;
	background: var(--pn-bg-alt);
	border-top: 1px solid rgba(255, 255, 255, 0.05);
	border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.section.alt > * {
	max-width: 1180px;
	margin-left: auto;
	margin-right: auto;
}

.section-head {
	max-width: 720px;
	margin-bottom: 38px;
}

.section-head h2 {
	margin: 0;
	font-size: clamp(28px, 3.6vw, 42px);
	line-height: 1.15;
	letter-spacing: -0.02em;
}

.section-head p {
	margin: 14px 0 0;
	color: var(--pn-muted);
	font-size: 15px;
}

.feature-grid {
	display: grid;
	grid-template-columns: repeat(3, minmax(0, 1fr));
	gap: 18px;
}

.feature {
	background: var(--pn-card);
	border: 1px solid var(--pn-border);
	border-radius: 16px;
	padding: 24px;
}

.feature-ico {
	display: inline-grid;
	place-items: center;
	width: 38px;
	height: 38px;
	margin-bottom: 18px;
	border-radius: 10px;
	background: rgba(64, 158, 255, 0.12);
	border: 1px solid rgba(64, 158, 255, 0.24);
	color: #8ec5ff;
	font-size: 12px;
	font-weight: 700;
}

.feature h3,
.step h3 {
	margin: 0 0 8px;
	font-size: 17px;
}

.feature p,
.step p {
	margin: 0;
	color: var(--pn-muted);
	font-size: 14px;
	line-height: 1.75;
}

.steps {
	display: grid;
	grid-template-columns: repeat(4, minmax(0, 1fr));
	gap: 18px;
	margin: 0;
	padding: 0;
	list-style: none;
}

.steps li {
	position: relative;
	background: var(--pn-card);
	border: 1px solid var(--pn-border);
	border-radius: 16px;
	padding: 24px;
}

.step-num {
	display: inline-grid;
	place-items: center;
	width: 34px;
	height: 34px;
	margin-bottom: 16px;
	border-radius: 99px;
	background: var(--pn-primary);
	color: #fff;
	font-size: 13px;
	font-weight: 700;
}

.pricing-wrap {
	display: grid;
	grid-template-columns: minmax(0, 1fr) minmax(0, 1.15fr);
	gap: 22px;
	align-items: start;
}

.price-card,
.terms-card,
.contact-card,
.checkout-card {
	background: var(--pn-card);
	border: 1px solid var(--pn-border);
	border-radius: 18px;
}

.price-card {
	padding: 28px;
}

.price-top {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 12px;
}

.plan-name {
	font-size: 18px;
	font-weight: 700;
}

.plan-badge {
	border: 1px solid rgba(64, 158, 255, 0.35);
	background: rgba(64, 158, 255, 0.12);
	color: #8ec5ff;
	border-radius: 99px;
	padding: 4px 10px;
	font-size: 11px;
	font-weight: 700;
}

.price {
	display: flex;
	align-items: baseline;
	gap: 4px;
	margin: 22px 0 10px;
}

.price .currency {
	font-size: 30px;
	font-weight: 600;
	color: #cfe6ff;
}

.price .amount {
	font-size: 56px;
	line-height: 1;
	font-weight: 700;
	letter-spacing: -0.04em;
}

.price .per {
	margin-left: 8px;
	color: var(--pn-faint);
	font-size: 13px;
}

.price-desc {
	margin: 0 0 20px;
	color: var(--pn-muted);
	font-size: 14px;
}

.price-desc b {
	color: var(--pn-text);
}

.price-list {
	margin: 0 0 22px;
	padding: 0;
	list-style: none;
	display: grid;
	gap: 10px;
}

.price-list li {
	position: relative;
	padding-left: 24px;
	color: var(--pn-muted);
	font-size: 14px;
}

.price-list li::before {
	content: '✓';
	position: absolute;
	left: 0;
	top: 0;
	color: var(--pn-green);
	font-weight: 700;
}

.price-note {
	margin: 12px 0 0;
	color: var(--pn-faint);
	font-size: 12px;
	text-align: center;
}

.terms-card {
	padding: 28px;
}

.terms-card h3 {
	margin: 0 0 18px;
	font-size: 18px;
}

.terms-card dl,
.contact-card dl {
	margin: 0;
	display: grid;
	gap: 14px;
}

.terms-card dl > div,
.contact-card dl > div {
	display: grid;
	grid-template-columns: 150px minmax(0, 1fr);
	gap: 16px;
}

.terms-card dt,
.contact-card dt {
	color: var(--pn-faint);
	font-size: 12px;
	font-weight: 600;
	letter-spacing: 0.05em;
	text-transform: uppercase;
}

.terms-card dd,
.contact-card dd {
	margin: 0;
	color: var(--pn-muted);
	font-size: 14px;
}

.terms-card dd b {
	color: var(--pn-text);
}

.legal-links {
	display: flex;
	flex-wrap: wrap;
	gap: 14px;
	margin-top: 22px;
	padding-top: 18px;
	border-top: 1px solid rgba(255, 255, 255, 0.07);
	font-size: 13px;
}

.legal-links a {
	color: #8ec5ff;
}

.legal-links a:hover {
	text-decoration: underline;
}

.checkout-card {
	max-width: 760px;
	margin: 0 auto;
	padding: 28px;
}

.checkout-product {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 20px;
	padding-bottom: 20px;
	border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.checkout-product b {
	display: block;
	font-size: 17px;
}

.checkout-product small {
	display: block;
	margin-top: 4px;
	color: var(--pn-faint);
	font-size: 12px;
}

.checkout-price {
	font-size: 28px;
	font-weight: 700;
	white-space: nowrap;
}

.checkout-lines {
	display: grid;
	gap: 12px;
	padding: 20px 0;
	border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.checkout-lines > div,
.checkout-total {
	display: flex;
	justify-content: space-between;
	gap: 20px;
}

.checkout-lines span {
	color: var(--pn-muted);
	font-size: 14px;
}

.checkout-lines b {
	font-size: 14px;
	text-align: right;
}

.checkout-total {
	align-items: baseline;
	padding: 20px 0;
}

.checkout-total span {
	color: var(--pn-muted);
	font-size: 14px;
}

.checkout-total b {
	font-size: 26px;
}

.checkout-actions {
	display: grid;
	gap: 10px;
}

.checkout-fine {
	margin: 16px 0 0;
	color: var(--pn-faint);
	font-size: 12px;
	text-align: center;
}

.checkout-fine a {
	color: #8ec5ff;
	text-decoration: underline;
}

.contact-grid {
	display: grid;
	grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr);
	gap: 22px;
}

.contact-card {
	padding: 28px;
}

.contact-card h3 {
	margin: 0 0 18px;
	font-size: 18px;
}

.contact-card p {
	margin: 0 0 18px;
	color: var(--pn-muted);
	font-size: 14px;
}

.contact-card a {
	color: #8ec5ff;
}

.policy-list {
	margin: 0 0 22px;
	padding: 0;
	list-style: none;
	display: grid;
	gap: 10px;
}

.policy-list a {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 16px;
	padding: 13px 15px;
	border: 1px solid var(--pn-border);
	border-radius: 10px;
	background: var(--pn-card-2);
	color: var(--pn-text);
	font-size: 14px;
}

.policy-list a:hover {
	border-color: #4a4a50;
	background: #27272b;
}

.policy-list span {
	color: #8ec5ff;
}

.footer {
	background: #151516;
	border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.footer-inner {
	display: grid;
	grid-template-columns: minmax(0, 1.2fr) minmax(0, 1.8fr);
	gap: 40px;
	max-width: 1180px;
	margin: 0 auto;
	padding: 48px 24px 32px;
}

.footer-brand img {
	width: 140px;
	height: auto;
}

.footer-brand p {
	margin: 14px 0 0;
	max-width: 340px;
	color: var(--pn-faint);
	font-size: 13px;
}

.footer-cols {
	display: grid;
	grid-template-columns: repeat(3, minmax(0, 1fr));
	gap: 24px;
}

.footer-cols > div {
	display: grid;
	align-content: start;
	gap: 8px;
}

.footer-cols b {
	margin-bottom: 4px;
	color: var(--pn-text);
	font-size: 12px;
	letter-spacing: 0.08em;
	text-transform: uppercase;
}

.footer-cols a {
	color: var(--pn-faint);
	font-size: 13px;
}

.footer-cols a:hover {
	color: var(--pn-text);
}

.footer-bottom {
	display: flex;
	flex-wrap: wrap;
	justify-content: space-between;
	gap: 8px;
	max-width: 1180px;
	margin: 0 auto;
	padding: 0 24px 28px;
	color: #6f7378;
	font-size: 11px;
}

@media (max-width: 980px) {
	.nav-links {
		display: none;
	}

	.hero-inner,
	.pricing-wrap,
	.contact-grid,
	.footer-inner {
		grid-template-columns: 1fr;
	}

	.hero-inner {
		padding-top: 64px;
		gap: 40px;
	}

	.feature-grid {
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}

	.steps {
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}
}

@media (max-width: 640px) {
	.nav-inner {
		padding: 14px 18px;
	}

	.brand img {
		width: 124px;
	}

	.nav-actions .ghost {
		display: none;
	}

	.nav-actions .btn.primary {
		padding: 9px 14px;
		font-size: 13px;
	}

	.hero-inner,
	.section {
		padding-left: 18px;
		padding-right: 18px;
	}

	.hero h1 {
		font-size: 38px;
	}

	.lead {
		font-size: 15px;
	}

	.hero-actions .btn {
		width: 100%;
	}

	.feature-grid,
	.steps,
	.footer-cols {
		grid-template-columns: 1fr;
	}

	.terms-card dl > div,
	.contact-card dl > div {
		grid-template-columns: 1fr;
		gap: 3px;
	}

	.checkout-product {
		align-items: flex-start;
		flex-direction: column;
	}

	.checkout-price {
		font-size: 24px;
	}

	.footer-bottom {
		flex-direction: column;
	}
}
</style>
