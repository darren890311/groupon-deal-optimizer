package server

import "testing"

func TestNormalizeURL(t *testing.T) {
	cases := []struct {
		name string
		in   string
		want string
	}{
		{"strips query", "https://www.groupon.com/deals/x?redemptionLocationId=abc", "https://www.groupon.com/deals/x"},
		{"strips trailing slash", "https://www.groupon.com/deals/x/", "https://www.groupon.com/deals/x"},
		{"strips both", "https://www.groupon.com/deals/x/?a=1&b=2", "https://www.groupon.com/deals/x"},
		{"already clean", "https://www.groupon.com/deals/x", "https://www.groupon.com/deals/x"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := normalizeURL(tc.in); got != tc.want {
				t.Errorf("normalizeURL(%q) = %q, want %q", tc.in, got, tc.want)
			}
		})
	}
}
