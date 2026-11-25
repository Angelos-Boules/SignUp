import React, { useState } from "react";

const PRICE = 25;

export function SignUpForm() {
    const [person, setPerson] = useState({
        firstName: "",
        lastName: "",
        phone: "",
        email: ""
    });

    const [guests, setGuests] = useState([]);
    const [submitting, setSubmitting] = useState(false);

    const payment = new URLSearchParams(window.location.search).get("payment");

    function updatePerson(field, value) {
        setPerson({ ...person, [field]: value });
    }

    function addGuest() {
        setGuests([...guests, { firstName: "", lastName: "", phone: "", email: "" }]);
    }

    function removeGuest(index) {
        setGuests(guests.filter((guest, i) => i !== index));
    }

    function updateGuest(index, field, value) {
        const updated = guests.map((guest, i) => {
            if (i === index) {
                return { ...guest, [field]: value };
            }
            return guest;
        });
        setGuests(updated);
    }

    async function handleSubmit(e) {
        e.preventDefault();
        if (submitting) {
            return;
        }
        setSubmitting(true);

        const registration = { ...person, guests: guests };

        try {
            const resp = await fetch("https://i71tfscl8f.execute-api.us-east-1.amazonaws.com/register", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(registration)
            });

            if (!resp.ok) {
                throw new Error("Request failed with status " + resp.status);
            }

            const data = await resp.json();
            window.location.href = data.checkoutUrl;
        } catch (error) {
            console.error(error);
            alert("Something went wrong. Please try again.");
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <form className="g-3" onSubmit={handleSubmit}>
            {payment === "success" && (
                <div className="alert alert-success">Payment received. You are signed up!</div>
            )}
            {payment === "cancelled" && (
                <div className="alert alert-warning">Payment was cancelled. You are not signed up yet.</div>
            )}

            <div className="row py-3">
                <div className="md:col-3">
                    <label htmlFor="firstName" className="form-label">First Name</label>
                    <input
                        type="text"
                        className="form-control"
                        id="firstName"
                        required
                        value={person.firstName}
                        onChange={(e) => updatePerson("firstName", e.target.value)}
                    />
                </div>
                <div className="md:col-3">
                    <label htmlFor="lastName" className="form-label">Last Name</label>
                    <input
                        type="text"
                        className="form-control"
                        id="lastName"
                        required
                        value={person.lastName}
                        onChange={(e) => updatePerson("lastName", e.target.value)}
                    />
                </div>
            </div>
            <div className="row py-3">
                <div className="md:col-3">
                    <label htmlFor="phoneNumber" className="form-label">Phone Number</label>
                    <input
                        type="tel"
                        className="form-control"
                        id="phoneNumber"
                        required
                        value={person.phone}
                        onChange={(e) => updatePerson("phone", e.target.value)}
                    />
                </div>
                <div className="md:col-3">
                    <label htmlFor="email" className="form-label">Email</label>
                    <input
                        type="email"
                        className="form-control"
                        id="email"
                        required
                        value={person.email}
                        onChange={(e) => updatePerson("email", e.target.value)}
                    />
                </div>
            </div>

            {guests.map((guest, index) => (
                <div key={index}>
                    <h5>Guest {index + 1}</h5>
                    <div className="row py-3">
                        <div className="md:col-3">
                            <label className="form-label">First Name</label>
                            <input
                                type="text"
                                className="form-control"
                                required
                                value={guest.firstName}
                                onChange={(e) => updateGuest(index, "firstName", e.target.value)}
                            />
                        </div>
                        <div className="md:col-3">
                            <label className="form-label">Last Name</label>
                            <input
                                type="text"
                                className="form-control"
                                required
                                value={guest.lastName}
                                onChange={(e) => updateGuest(index, "lastName", e.target.value)}
                            />
                        </div>
                    </div>
                    <div className="row py-3">
                        <div className="md:col-3">
                            <label className="form-label">Phone Number</label>
                            <input
                                type="tel"
                                className="form-control"
                                value={guest.phone}
                                onChange={(e) => updateGuest(index, "phone", e.target.value)}
                            />
                        </div>
                        <div className="md:col-3">
                            <label className="form-label">Email</label>
                            <input
                                type="email"
                                className="form-control"
                                value={guest.email}
                                onChange={(e) => updateGuest(index, "email", e.target.value)}
                            />
                        </div>
                        <div className="md:col-3 d-flex align-items-end">
                            <button
                                type="button"
                                className="btn btn-outline-danger"
                                onClick={() => removeGuest(index)}
                            >
                                Remove
                            </button>
                        </div>
                    </div>
                </div>
            ))}

            <div className="col-12 py-3">
                <button type="button" className="btn btn-secondary" onClick={addGuest}>
                    Add Guest
                </button>
            </div>

            <div className="col-12">
                <p>Total: ${PRICE * (1 + guests.length)} (${PRICE} per person, guests included)</p>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                    {submitting ? "Going to payment..." : "Continue to payment"}
                </button>
            </div>
        </form>
    );
}